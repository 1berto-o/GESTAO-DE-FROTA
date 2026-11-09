from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.utils import timezone

from .models import (
    Usuario,
    Setor,
    DocumentoCNH,
    resumo_cnh_usuario,
    cnh_pendente,
    CNH_DIAS_ALERTA_VENCIMENTO,
    normalizar_nome_setor,
)
from .text_utils import aplicar_maiusculas
from .validators import validar_matricula, validar_telefone
from auditoria.services import exigir_justificativa
from django.core.exceptions import ValidationError as DjangoValidationError


class SetorSerializer(serializers.ModelSerializer):
    usuarios_count = serializers.IntegerField(read_only=True, required=False)
    usuarios_ativos_count = serializers.IntegerField(read_only=True, required=False)
    usuarios_inativos_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Setor
        fields = [
            'id', 'nome', 'descricao', 'ativo',
            'usuarios_count', 'usuarios_ativos_count', 'usuarios_inativos_count',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = [
            'id', 'criado_em', 'atualizado_em',
            'usuarios_count', 'usuarios_ativos_count', 'usuarios_inativos_count',
        ]

    def validate_nome(self, value):
        nome = ' '.join((value or '').strip().split())
        if not nome:
            raise serializers.ValidationError('Informe o nome do setor.')
        chave = normalizar_nome_setor(nome)
        qs = Setor.objects.filter(nome_normalizado=chave)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Já existe um setor com este nome (sem diferenciar maiúsculas/minúsculas).'
            )
        return nome

    def validate_ativo(self, value):
        """Desativação só é permitida sem usuários ativos vinculados."""
        if value is False and self.instance is not None and self.instance.ativo:
            ativos = self.instance.usuarios.filter(is_active=True).count()
            if ativos:
                raise serializers.ValidationError(
                    f'Não é possível desativar: existem {ativos} usuário(s) ativo(s) '
                    'vinculado(s). Transfira ou remova o vínculo antes de desativar.'
                )
        return value


class SetorUsuarioResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'matricula', 'nome', 'email', 'is_admin', 'is_active']


class SetorTransferenciaSerializer(serializers.Serializer):
    """Transfere ou remove vínculo de usuários de um setor (admin)."""

    usuario_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    setor_destino_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    def validate_usuario_ids(self, value):
        ids = list(dict.fromkeys(value))
        if not ids:
            raise serializers.ValidationError('Informe ao menos um usuário.')
        return ids

    def validate(self, attrs):
        setor_origem = self.context['setor']
        destino_id = attrs.get('setor_destino_id', None)
        if 'setor_destino_id' in self.initial_data and destino_id is None:
            attrs['setor_destino'] = None
        elif destino_id is None:
            attrs['setor_destino'] = None
        else:
            if destino_id == setor_origem.id:
                raise serializers.ValidationError({
                    'setor_destino_id': ['O setor de destino deve ser diferente do atual.'],
                })
            try:
                destino = Setor.objects.get(pk=destino_id)
            except Setor.DoesNotExist:
                raise serializers.ValidationError({
                    'setor_destino_id': ['Setor de destino não encontrado.'],
                })
            if not destino.ativo:
                raise serializers.ValidationError({
                    'setor_destino_id': [
                        'Não é possível transferir para um setor inativo.',
                    ],
                })
            attrs['setor_destino'] = destino

        existentes = set(
            Usuario.objects.filter(
                id__in=attrs['usuario_ids'],
                setor_id=setor_origem.id,
            ).values_list('id', flat=True)
        )
        faltando = [uid for uid in attrs['usuario_ids'] if uid not in existentes]
        if faltando:
            raise serializers.ValidationError({
                'usuario_ids': [
                    'Um ou mais usuários não pertencem a este setor '
                    f'(ids: {", ".join(str(i) for i in faltando)}).'
                ],
            })
        attrs['usuario_ids'] = list(existentes)
        return attrs


def _validar_setor_vinculo(setor, *, instancia=None):
    """Aceita null; exige setor existente; só permite inativo se já for o vínculo atual."""
    if setor is None:
        return None
    if not setor.ativo:
        if instancia is not None and instancia.setor_id == setor.id:
            return setor
        raise serializers.ValidationError(
            'Não é possível vincular a um setor inativo. Selecione um setor ativo.'
        )
    return setor


class DocumentoCNHSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    usuario_matricula = serializers.CharField(source='usuario.matricula', read_only=True)
    admin_aprovador_nome = serializers.CharField(
        source='admin_aprovador.nome', read_only=True
    )
    arquivo_url = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    esta_vencida = serializers.BooleanField(read_only=True)
    proxima_do_vencimento = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentoCNH
        fields = [
            'id', 'usuario', 'usuario_nome', 'usuario_matricula',
            'data_validade', 'arquivo', 'arquivo_url',
            'status', 'admin_aprovador', 'admin_aprovador_nome',
            'data_decisao', 'observacao_admin',
            'dias_restantes', 'esta_vencida', 'proxima_do_vencimento',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = [
            'id', 'usuario', 'data_validade', 'status', 'admin_aprovador',
            'data_decisao', 'observacao_admin',
            'criado_em', 'atualizado_em',
        ]

    def get_dias_restantes(self, obj):
        return obj.dias_restantes

    def get_arquivo_url(self, obj):
        from config.media_access import url_midia_assinada
        request = self.context.get('request')
        if not obj.arquivo or not request:
            return None
        user = request.user
        if not user.is_authenticated:
            return None
        if not user.is_admin and obj.usuario_id != user.id:
            return None
        return url_midia_assinada(request, obj.arquivo)


class DocumentoCNHCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoCNH
        fields = ['arquivo']

    def validate(self, data):
        usuario = self.context['request'].user
        if cnh_pendente(usuario):
            raise serializers.ValidationError(
                'Você já possui uma CNH aguardando aprovação do gestor.'
            )
        return data

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        validated_data['status'] = 'pendente'
        validated_data['data_validade'] = None
        return super().create(validated_data)


class DocumentoCNHDecisaoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['aprovado', 'rejeitado'])
    data_validade = serializers.DateField(required=False, allow_null=True)
    observacao_admin = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get('status') == 'aprovado':
            if not data.get('data_validade'):
                raise serializers.ValidationError({
                    'data_validade': [
                        'Informe a data de validade da CNH para aprovar o documento.'
                    ]
                })
            if data['data_validade'] < timezone.localdate():
                raise serializers.ValidationError({
                    'data_validade': [
                        'A data de validade não pode estar no passado.'
                    ]
                })
        if data.get('status') == 'rejeitado':
            data['observacao_admin'] = exigir_justificativa(data.get('observacao_admin'))
        aplicar_maiusculas(data, ['observacao_admin'])
        return data

    def update(self, instance, validated_data):
        admin_user = self.context['request'].user
        observacao = validated_data.get('observacao_admin', '')
        if validated_data['status'] == 'aprovado':
            instance.aprovar(admin_user, validated_data['data_validade'], observacao)
        else:
            instance.rejeitar(admin_user, observacao)
        return instance


class UsuarioSerializer(serializers.ModelSerializer):
    cnh = serializers.SerializerMethodField()
    termo = serializers.SerializerMethodField()
    setor = serializers.PrimaryKeyRelatedField(read_only=True)
    setor_nome = serializers.CharField(source='setor.nome', read_only=True, default=None)
    setor_ativo = serializers.BooleanField(source='setor.ativo', read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            'id', 'matricula', 'nome', 'email', 'telefone',
            'setor', 'setor_nome', 'setor_ativo',
            'is_admin', 'is_active', 'precisa_definir_senha', 'criado_em',
            'cnh', 'termo',
        ]
        read_only_fields = ['id', 'criado_em', 'precisa_definir_senha']

    def get_cnh(self, obj):
        if obj.is_admin:
            return None
        return resumo_cnh_usuario(obj)

    def get_termo(self, obj):
        if obj.is_admin:
            return None
        from termos.services_conta import resumo_termo_usuario
        return resumo_termo_usuario(obj)


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Admin cria usuário sem senha; conta fica em primeiro acesso."""

    matricula = serializers.CharField(
        max_length=50,
        validators=[
            UniqueValidator(
                queryset=Usuario.objects.all(),
                message='Esta matrícula já está cadastrada.',
            )
        ],
        error_messages={
            'blank': 'Informe a matrícula.',
            'required': 'Informe a matrícula.',
        },
    )
    setor = serializers.PrimaryKeyRelatedField(
        queryset=Setor.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Usuario
        fields = [
            'matricula', 'nome', 'email', 'telefone', 'setor',
            'is_admin', 'is_active',
        ]
        extra_kwargs = {
            'nome': {
                'error_messages': {
                    'blank': 'Informe o nome completo.',
                    'required': 'Informe o nome completo.',
                },
            },
        }

    def validate_matricula(self, value):
        try:
            return validar_matricula(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate_telefone(self, value):
        try:
            return validar_telefone(value) or None
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate_setor(self, value):
        return _validar_setor_vinculo(value)

    def validate(self, data):
        aplicar_maiusculas(data, ['nome'])
        return data

    def create(self, validated_data):
        return Usuario.objects.create_user(
            password=None,
            precisa_definir_senha=True,
            **validated_data,
        )


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    setor = serializers.PrimaryKeyRelatedField(
        queryset=Setor.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'telefone', 'setor', 'is_active']

    def validate_is_active(self, value):
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_admin', False):
            raise serializers.ValidationError(
                'Apenas administradores podem alterar o status da conta.'
            )
        return value

    def validate_telefone(self, value):
        try:
            return validar_telefone(value) or None
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate_setor(self, value):
        return _validar_setor_vinculo(value, instancia=self.instance)

    def validate(self, data):
        aplicar_maiusculas(data, ['nome'])
        return data


class PerfilSerializer(serializers.ModelSerializer):
    cnh = serializers.SerializerMethodField()
    cnh_dias_alerta = serializers.SerializerMethodField()
    termo = serializers.SerializerMethodField()
    setor = serializers.PrimaryKeyRelatedField(read_only=True)
    setor_nome = serializers.CharField(source='setor.nome', read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            'id', 'matricula', 'nome', 'email', 'telefone',
            'setor', 'setor_nome',
            'is_admin', 'is_active', 'precisa_definir_senha',
            'cnh', 'cnh_dias_alerta', 'termo',
        ]

    def get_cnh(self, obj):
        return resumo_cnh_usuario(obj)

    def get_cnh_dias_alerta(self, obj):
        return CNH_DIAS_ALERTA_VENCIMENTO

    def get_termo(self, obj):
        from termos.services_conta import resumo_termo_usuario, sincronizar_status_conta
        sincronizar_status_conta(obj)
        obj.refresh_from_db(fields=['is_active'])
        return resumo_termo_usuario(obj)
