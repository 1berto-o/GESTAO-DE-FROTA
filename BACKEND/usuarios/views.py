from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes

from termos.models import TermoResponsabilidade
from termos.services_conta import situacao_termo
from .models import (
    DocumentoCNH,
    Setor,
    SolicitacaoRecuperacaoSenha,
    resumo_cnh_usuario,
    CNH_DIAS_ALERTA_VENCIMENTO,
)
from .serializers import (
    UsuarioSerializer, UsuarioCreateSerializer,
    UsuarioUpdateSerializer, PerfilSerializer,
    SetorSerializer, SetorUsuarioResumoSerializer, SetorTransferenciaSerializer,
    DocumentoCNHSerializer, DocumentoCNHCreateSerializer,
    DocumentoCNHDecisaoSerializer,
)
from .auth import (
    CustomTokenObtainPairSerializer,
    DefinirSenhaSerializer,
    SolicitarRecuperacaoSenhaSerializer,
    RedefinirSenhaCodigoSerializer,
    RejeitarRecuperacaoSerializer,
)
from . import recuperacao as recuperacao_svc
from auditoria.services import registrar
from .permissions import AuthenticatedAndPasswordSet, IsAdmin

Usuario = get_user_model()


def _inclui_inativos(request):
    return (request.query_params.get('incluir_inativos') or '').lower() in ('1', 'true', 'sim')


def _lista_param(request, nome):
    valor = request.query_params.get(nome) or ''
    return {item.strip() for item in valor.split(',') if item.strip()}


class PendenciasAdminView(APIView):
    """
    GET /api/usuarios/pendencias/ — contadores do painel administrativo.

    CNH considera funcionários ativos; Termo considera todos os funcionários,
    porque termo vencido ou rejeitado é o que inativa a conta. Admins ficam fora.
    """
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def get(self, request):
        funcionarios = Usuario.objects.filter(is_admin=False)

        cnh = {'vencida': 0, 'proxima_vencimento': 0, 'regularizar': 0}
        for usuario in funcionarios.filter(is_active=True):
            situacao = resumo_cnh_usuario(usuario)['situacao']
            if situacao in ('vencida', 'proxima_vencimento'):
                cnh[situacao] += 1
            elif situacao in ('sem_cnh', 'rejeitada'):
                cnh['regularizar'] += 1

        termo = {'vencido': 0, 'regularizar': 0}
        for usuario in funcionarios:
            situacao, _ = situacao_termo(usuario)
            if situacao == 'vencido':
                termo['vencido'] += 1
            elif situacao in ('sem_termo', 'rejeitado'):
                termo['regularizar'] += 1

        recuperacao_pendentes = SolicitacaoRecuperacaoSenha.objects.filter(
            status=SolicitacaoRecuperacaoSenha.Status.PENDENTE,
        ).count()

        return Response({
            'cnh': {
                'pendentes_analise': DocumentoCNH.objects.filter(
                    status='pendente', usuario__is_admin=False,
                ).count(),
                'vencidas': cnh['vencida'],
                'proximas_vencimento': cnh['proxima_vencimento'],
                'sem_cnh_valida': cnh['regularizar'],
                'dias_alerta': CNH_DIAS_ALERTA_VENCIMENTO,
            },
            'termo': {
                'pendentes_analise': TermoResponsabilidade.objects.filter(
                    status='pendente', usuario__is_admin=False,
                ).count(),
                'vencidos': termo['vencido'],
                'sem_termo_valido': termo['regularizar'],
            },
            'contas_inativas': funcionarios.filter(is_active=False).count(),
            'recuperacao_senha': {
                'pendentes': recuperacao_pendentes,
            },
        })


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class PerfilView(APIView):
    """
    GET /api/usuarios/perfil/
    Retorna os dados do usuário autenticado (inclui resumo da CNH).
    """
    permission_classes = AuthenticatedAndPasswordSet
    allow_primeiro_acesso = True

    def get(self, request):
        serializer = PerfilSerializer(request.user)
        return Response(serializer.data)


class DefinirSenhaView(APIView):
    """
    POST /api/usuarios/definir-senha/
    Define a senha no primeiro acesso.
    """
    permission_classes = AuthenticatedAndPasswordSet
    allow_primeiro_acesso = True

    def post(self, request):
        if not request.user.precisa_definir_senha:
            return Response(
                {'detail': 'Sua senha já foi definida.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = DefinirSenhaSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        registrar(
            ator=request.user,
            acao='definir_senha',
            entidade='usuario',
            entidade_id=request.user.id,
            identificacao=f'{request.user.nome} ({request.user.matricula})',
            descricao=f'{request.user.nome} definiu a senha de acesso.',
        )
        return Response({
            'detail': 'Senha definida com sucesso.',
            'precisa_definir_senha': False,
            'perfil': PerfilSerializer(request.user).data,
        })


class RedefinirSenhaAdminView(APIView):
    """
    Endpoint legado desativado.
    O administrador não define a senha do usuário — usa o fluxo de recuperação.
    """
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def post(self, request, pk):
        return Response(
            {
                'detail': (
                    'A redefinição direta pelo administrador foi desativada. '
                    'Use o fluxo: solicitação do usuário → aprovação com código de uso único.'
                ),
            },
            status=status.HTTP_410_GONE,
        )


class SolicitarRecuperacaoSenhaView(APIView):
    """POST /api/usuarios/recuperacao-senha/solicitar/ — público."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = None

    def post(self, request):
        serializer = SolicitarRecuperacaoSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        matricula = serializer.validated_data['matricula']
        resultado = recuperacao_svc.solicitar_recuperacao(
            matricula=matricula, request=request,
        )
        criada = resultado.pop('_criada', None)
        if criada is not None:
            registrar(
                ator=criada.usuario,
                acao='solicitar_recuperacao_senha',
                entidade='usuario',
                entidade_id=criada.usuario_id,
                identificacao=f'{criada.usuario.nome} ({criada.matricula})',
                descricao='Solicitação de recuperação de senha registrada.',
                usuario_afetado=criada.usuario,
                detalhes={'solicitacao_id': criada.id},
            )
        return Response(resultado, status=status.HTTP_200_OK)


class RecuperacaoSenhaAdminListView(APIView):
    """GET /api/usuarios/recuperacao-senha/ — admin lista solicitações."""
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def get(self, request):
        status_filtro = (request.query_params.get('status') or 'pendente').strip()
        qs = SolicitacaoRecuperacaoSenha.objects.select_related('usuario', 'admin_decisor')
        if status_filtro and status_filtro != 'todas':
            qs = qs.filter(status=status_filtro)
        dados = [
            {
                'id': s.id,
                'matricula': s.matricula,
                'usuario_id': s.usuario_id,
                'usuario_nome': s.usuario.nome,
                'status': s.status,
                'solicitado_em': s.solicitado_em,
                'decidido_em': s.decidido_em,
                'codigo_expira_em': s.codigo_expira_em,
                'admin_decisor_nome': s.admin_decisor.nome if s.admin_decisor_id else None,
                'observacao_admin': s.observacao_admin,
            }
            for s in qs[:100]
        ]
        return Response({'results': dados, 'count': len(dados)})


class AprovarRecuperacaoSenhaView(APIView):
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def post(self, request, pk):
        try:
            solicitacao = SolicitacaoRecuperacaoSenha.objects.select_related('usuario').get(pk=pk)
        except SolicitacaoRecuperacaoSenha.DoesNotExist:
            return Response({'detail': 'Solicitação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            codigo = recuperacao_svc.aprovar_solicitacao(
                solicitacao=solicitacao, admin=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        registrar(
            ator=request.user,
            acao='aprovar_recuperacao_senha',
            entidade='usuario',
            entidade_id=solicitacao.usuario_id,
            identificacao=f'{solicitacao.usuario.nome} ({solicitacao.matricula})',
            descricao='Código de recuperação gerado (exibido uma vez ao administrador).',
            usuario_afetado=solicitacao.usuario,
            detalhes={'solicitacao_id': solicitacao.id, 'validade_minutos': 30},
        )
        return Response({
            'detail': 'Solicitação aprovada. Entregue o código ao usuário por canal confiável.',
            'codigo': codigo,
            'expira_em': solicitacao.codigo_expira_em,
            'matricula': solicitacao.matricula,
            'usuario_nome': solicitacao.usuario.nome,
            'aviso': 'Este código não será exibido novamente.',
        })


class RejeitarRecuperacaoSenhaView(APIView):
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def post(self, request, pk):
        try:
            solicitacao = SolicitacaoRecuperacaoSenha.objects.select_related('usuario').get(pk=pk)
        except SolicitacaoRecuperacaoSenha.DoesNotExist:
            return Response({'detail': 'Solicitação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        ser = RejeitarRecuperacaoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            recuperacao_svc.rejeitar_solicitacao(
                solicitacao=solicitacao,
                admin=request.user,
                observacao=ser.validated_data.get('observacao', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        registrar(
            ator=request.user,
            acao='rejeitar_recuperacao_senha',
            entidade='usuario',
            entidade_id=solicitacao.usuario_id,
            identificacao=f'{solicitacao.usuario.nome} ({solicitacao.matricula})',
            descricao='Solicitação de recuperação de senha rejeitada.',
            usuario_afetado=solicitacao.usuario,
            justificativa=ser.validated_data.get('observacao', ''),
        )
        return Response({'detail': 'Solicitação rejeitada.'})


class RedefinirSenhaComCodigoView(APIView):
    """POST /api/usuarios/recuperacao-senha/redefinir/ — público."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RedefinirSenhaCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            usuario = recuperacao_svc.redefinir_com_codigo(
                matricula=data['matricula'],
                codigo=data['codigo'],
                password=data['password'],
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        registrar(
            ator=usuario,
            acao='redefinir_senha_codigo',
            entidade='usuario',
            entidade_id=usuario.id,
            identificacao=f'{usuario.nome} ({usuario.matricula})',
            descricao='Senha redefinida com código de recuperação.',
            usuario_afetado=usuario,
        )
        return Response({
            'detail': 'Senha redefinida com sucesso. Faça login com a nova senha.',
        })


class UsuarioListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/usuarios/        -> Lista usuários (admin)
    POST /api/usuarios/        -> Cria usuário (admin)
    """
    queryset = Usuario.objects.select_related('setor').all()
    permission_classes = AuthenticatedAndPasswordSet

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def get_queryset(self):
        queryset = Usuario.objects.select_related('setor').all()
        ativo = self.request.query_params.get('ativo')
        setor = self.request.query_params.get('setor')
        cnh_situacoes = _lista_param(self.request, 'cnh_situacao')
        termo_situacoes = _lista_param(self.request, 'termo_situacao')
        if ativo is not None:
            queryset = queryset.filter(is_active=ativo.lower() == 'true')
        elif not _inclui_inativos(self.request):
            queryset = queryset.filter(is_active=True)
        if setor:
            if str(setor).isdigit():
                queryset = queryset.filter(setor_id=int(setor))
            else:
                queryset = queryset.filter(setor__nome__icontains=setor)
        # Filtros de CNH/Termo reutilizam as regras de situação, aplicadas em
        # memória; admins não possuem CNH nem Termo e ficam fora do resultado.
        if cnh_situacoes:
            ids = [
                u.id for u in queryset.filter(is_admin=False)
                if resumo_cnh_usuario(u)['situacao'] in cnh_situacoes
            ]
            queryset = queryset.filter(id__in=ids)
        if termo_situacoes:
            ids = [
                u.id for u in queryset.filter(is_admin=False)
                if situacao_termo(u)[0] in termo_situacoes
            ]
            queryset = queryset.filter(id__in=ids)
        return queryset

    def list(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem listar usuários.'
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied('Apenas administradores podem criar usuários.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        registrar(
            ator=request.user,
            acao='criar_usuario',
            entidade='usuario',
            entidade_id=usuario.id,
            identificacao=f'{usuario.nome} ({usuario.matricula})',
            descricao=(
                f'Usuário {usuario.nome} (matrícula {usuario.matricula}) foi cadastrado '
                f'como {"administrador" if usuario.is_admin else "funcionário"}.'
            ),
            detalhes={
                'perfil': 'administrador' if usuario.is_admin else 'funcionario',
                'setor': usuario.setor.nome if usuario.setor_id else '',
            },
        )
        out = UsuarioSerializer(usuario, context=self.get_serializer_context())
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)


class UsuarioDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/usuarios/<id>/  -> Detalhes do usuário
    PATCH  /api/usuarios/<id>/  -> Atualiza usuário
    DELETE /api/usuarios/<id>/  -> Remove usuário
    """
    queryset = Usuario.objects.select_related('setor').all()
    serializer_class = UsuarioUpdateSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_object(self):
        obj = super().get_object()
        if not self.request.user.is_admin and obj.id != self.request.user.id:
            raise PermissionDenied(
                'Você não tem permissão para acessar este usuário.'
            )
        return obj

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UsuarioSerializer
        return UsuarioUpdateSerializer

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem remover usuários.'
            )
        if instance.pk == self.request.user.pk:
            raise PermissionDenied(
                'Você não pode remover a própria conta.'
            )
        # Soft-delete: inativa o usuário e preserva o histórico relacionado.
        if not instance.is_active:
            return
        instance.is_active = False
        instance.save(update_fields=['is_active', 'atualizado_em'])
        registrar(
            ator=self.request.user,
            acao='inativar_usuario',
            entidade='usuario',
            entidade_id=instance.id,
            identificacao=f'{instance.nome} ({instance.matricula})',
            descricao=f'A conta de {instance.nome} (matrícula {instance.matricula}) foi desativada.',
        )

    def perform_update(self, serializer):
        if not self.request.user.is_admin:
            raise PermissionDenied('Apenas administradores podem alterar usuários.')
        anterior = serializer.instance
        campos = {}
        for campo in ('nome', 'email', 'telefone', 'setor', 'is_active'):
            if campo not in serializer.validated_data:
                continue
            if serializer.validated_data[campo] != getattr(anterior, campo):
                campos[campo] = serializer.validated_data[campo]
        serializer.save()
        if not campos:
            return
        usuario = serializer.instance
        if 'is_active' in campos and len(campos) == 1:
            acao = 'ativar_usuario' if usuario.is_active else 'inativar_usuario'
            efeito = 'ativada' if usuario.is_active else 'desativada'
            descricao = f'A conta de {usuario.nome} foi {efeito}.'
        elif 'is_active' in campos:
            acao = 'ativar_usuario' if usuario.is_active else 'inativar_usuario'
            descricao = f'A conta de {usuario.nome} foi atualizada.'
        else:
            acao = 'alterar_usuario'
            descricao = f'Os dados de {usuario.nome} foram atualizados.'
        rotulos = {
            'nome': 'nome',
            'email': 'e-mail',
            'telefone': 'telefone',
            'setor': 'setor',
            'is_active': 'situação da conta',
        }
        registrar(
            ator=self.request.user,
            acao=acao,
            entidade='usuario',
            entidade_id=usuario.id,
            identificacao=f'{usuario.nome} ({usuario.matricula})',
            descricao=descricao,
            detalhes={'campos': [rotulos.get(campo, campo) for campo in sorted(campos)]},
        )


def _queryset_setores_anotado():
    return Setor.objects.annotate(
        usuarios_count=Count('usuarios'),
        usuarios_ativos_count=Count('usuarios', filter=Q(usuarios__is_active=True)),
        usuarios_inativos_count=Count('usuarios', filter=Q(usuarios__is_active=False)),
    ).order_by('nome')


class SetorListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/usuarios/setores/ — lista setores (admin)
    POST /api/usuarios/setores/ — cria setor (admin)
    """
    serializer_class = SetorSerializer
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def get_queryset(self):
        qs = _queryset_setores_anotado()
        ativo = self.request.query_params.get('ativo')
        busca = (self.request.query_params.get('q') or '').strip()
        if ativo is not None:
            qs = qs.filter(ativo=ativo.lower() in ('1', 'true', 'sim'))
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca) | Q(descricao__icontains=busca)
            )
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        setor = serializer.save()
        setor = _queryset_setores_anotado().get(pk=setor.pk)
        out = SetorSerializer(setor, context=self.get_serializer_context())
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)


class SetorDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/usuarios/setores/<id>/
    Desativação lógica via PATCH {ativo: false} — bloqueada se houver usuários ativos.
    """
    serializer_class = SetorSerializer
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]
    queryset = Setor.objects.all()

    def get_queryset(self):
        return _queryset_setores_anotado()


class SetorUsuariosView(APIView):
    """GET /api/usuarios/setores/<id>/usuarios/ — membros do setor (admin)."""

    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def get(self, request, pk):
        setor = get_object_or_404(_queryset_setores_anotado(), pk=pk)
        ativos_apenas = (request.query_params.get('ativos') or '').lower() in (
            '1', 'true', 'sim',
        )
        qs = setor.usuarios.order_by('nome')
        if ativos_apenas:
            qs = qs.filter(is_active=True)
        return Response({
            'setor': SetorSerializer(setor).data,
            'usuarios': SetorUsuarioResumoSerializer(qs, many=True).data,
        })


class SetorTransferenciaView(APIView):
    """
    POST /api/usuarios/setores/<id>/transferir/
    Body: { usuario_ids: [...], setor_destino_id: <id|null> }
    Remove o vínculo (null) ou move para outro setor ativo, em uma transação.
    """

    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def post(self, request, pk):
        setor = get_object_or_404(Setor, pk=pk)
        serializer = SetorTransferenciaSerializer(
            data=request.data,
            context={'setor': setor, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        destino = serializer.validated_data['setor_destino']
        ids = serializer.validated_data['usuario_ids']

        with transaction.atomic():
            atualizados = (
                Usuario.objects
                .select_for_update()
                .filter(id__in=ids, setor_id=setor.id)
            )
            qtd = atualizados.update(setor=destino)
            if qtd != len(ids):
                raise ValidationError({
                    'usuario_ids': [
                        'A composição do setor mudou durante a operação. Tente novamente.',
                    ],
                })

        destino_nome = destino.nome if destino else None
        registrar(
            ator=request.user,
            acao='alterar_usuario',
            entidade='usuario',
            entidade_id=None,
            identificacao=setor.nome,
            descricao=(
                f'{qtd} usuário(s) do setor "{setor.nome}" '
                + (
                    f'transferido(s) para "{destino_nome}".'
                    if destino
                    else 'tiveram o vínculo de setor removido.'
                )
            ),
            detalhes={
                'setor_origem_id': setor.id,
                'setor_destino_id': destino.id if destino else None,
                'usuario_ids': ids,
                'quantidade': qtd,
            },
        )
        setor_atual = _queryset_setores_anotado().get(pk=setor.pk)
        return Response({
            'atualizados': qtd,
            'setor': SetorSerializer(setor_atual).data,
        })


class MeuStatusCNHView(APIView):
    """GET /api/usuarios/cnh/meu-status/"""
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request):
        resumo = resumo_cnh_usuario(request.user)
        vigente = None
        pendente = None
        docs = DocumentoCNH.objects.filter(usuario=request.user).order_by('-criado_em')[:5]
        for doc in docs:
            if doc.status == 'aprovado' and vigente is None and not doc.esta_vencida:
                vigente = doc
            if doc.status == 'pendente' and pendente is None:
                pendente = doc
        return Response({
            **resumo,
            'vigente': DocumentoCNHSerializer(vigente, context={'request': request}).data if vigente else None,
            'pendente': DocumentoCNHSerializer(pendente, context={'request': request}).data if pendente else None,
        })


class DocumentoCNHListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/usuarios/cnh/  -> Admin: lista (filtro ?status=pendente);
                                usuário: só as próprias.
    POST /api/usuarios/cnh/  -> Usuário envia nova CNH (multipart).
    """
    permission_classes = AuthenticatedAndPasswordSet
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DocumentoCNHCreateSerializer
        return DocumentoCNHSerializer

    def get_queryset(self):
        user = self.request.user
        qs = DocumentoCNH.objects.all() if user.is_admin else DocumentoCNH.objects.filter(usuario=user)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.select_related('usuario', 'admin_aprovador')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()
        registrar(
            ator=request.user,
            acao='enviar_cnh',
            entidade='cnh',
            entidade_id=doc.id,
            identificacao=f'CNH de {request.user.nome}',
            descricao=f'{request.user.nome} enviou uma CNH para análise.',
        )
        output = DocumentoCNHSerializer(doc, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class DocumentoCNHDecisaoView(generics.UpdateAPIView):
    """PATCH /api/usuarios/cnh/<id>/decisao/ — somente admin."""
    queryset = DocumentoCNH.objects.all()
    serializer_class = DocumentoCNHDecisaoSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_object(self):
        obj = super().get_object()
        if obj.status != 'pendente':
            raise PermissionDenied('Este documento já foi analisado.')
        return obj

    def update(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem aprovar ou rejeitar CNH.'
            )
        instance = self.get_object()
        if instance.usuario_id == request.user.id:
            raise PermissionDenied('Você não pode aprovar a própria CNH.')
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        acao = 'aprovar_cnh' if instance.status == 'aprovado' else 'rejeitar_cnh'
        resultado = 'aprovada' if instance.status == 'aprovado' else 'rejeitada'
        registrar(
            ator=request.user,
            acao=acao,
            entidade='cnh',
            entidade_id=instance.id,
            identificacao=f'CNH de {instance.usuario.nome}',
            descricao=f'A CNH de {instance.usuario.nome} foi {resultado}.',
            justificativa='' if instance.status == 'aprovado' else instance.observacao_admin,
            usuario_afetado=instance.usuario,
        )
        output = DocumentoCNHSerializer(instance, context={'request': request})
        return Response(output.data)


@api_view(['GET'])
@permission_classes(AuthenticatedAndPasswordSet)
def documento_cnh_detail(request, pk):
    """GET /api/usuarios/cnh/<id>/ — dono ou admin."""
    try:
        doc = DocumentoCNH.objects.get(pk=pk)
    except DocumentoCNH.DoesNotExist:
        return Response({'detail': 'Documento não encontrado.'}, status=404)
    if not request.user.is_admin and doc.usuario_id != request.user.id:
        return Response({'detail': 'Sem permissão.'}, status=403)
    return Response(DocumentoCNHSerializer(doc, context={'request': request}).data)
