from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone


# Dias para alerta de CNH próxima do vencimento.
CNH_DIAS_ALERTA_VENCIMENTO = 30


def normalizar_nome_setor(nome: str) -> str:
    """Normaliza para unicidade case-insensitive (espaços colapsados)."""
    return ' '.join((nome or '').strip().casefold().split())


class Setor(models.Model):
    """Cadastro administrativo de setores da organização."""

    nome = models.CharField('Nome', max_length=100)
    nome_normalizado = models.CharField(
        'Nome normalizado',
        max_length=100,
        unique=True,
        editable=False,
        db_index=True,
    )
    descricao = models.TextField('Descrição', blank=True, default='')
    ativo = models.BooleanField('Ativo', default=True, db_index=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Setor'
        verbose_name_plural = 'Setores'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.nome = ' '.join((self.nome or '').strip().split())
        self.nome_normalizado = normalizar_nome_setor(self.nome)
        super().save(*args, **kwargs)


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, matricula, nome, password=None, **extra_fields):
        if not matricula:
            raise ValueError('A matrícula deve ser fornecida')
        if not nome:
            raise ValueError('O nome deve ser fornecido')

        precisa = extra_fields.pop('precisa_definir_senha', None)
        user = self.model(matricula=matricula, nome=nome, **extra_fields)

        if password:
            user.set_password(password)
            user.precisa_definir_senha = False if precisa is None else precisa
        else:
            user.set_unusable_password()
            user.precisa_definir_senha = True if precisa is None else precisa

        user.save(using=self._db)
        return user

    def create_superuser(self, matricula, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('precisa_definir_senha', False)

        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        if not password:
            raise ValueError('Superuser must have a password.')

        return self.create_user(matricula, nome, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    matricula = models.CharField(
        'Matrícula',
        max_length=50,
        unique=True,
        help_text=(
            'Identificador único do funcionário. Apenas dígitos (0-9), '
            'até 50 caracteres; zeros à esquerda são preservados.'
        ),
    )
    nome = models.CharField('Nome completo', max_length=150)
    email = models.EmailField('E-mail', blank=True, null=True)
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True,
        null=True,
        help_text='Telefone com DDD (somente dígitos na persistência).',
    )
    setor = models.ForeignKey(
        Setor,
        on_delete=models.PROTECT,
        related_name='usuarios',
        verbose_name='Setor',
        blank=True,
        null=True,
    )

    is_admin = models.BooleanField('Administrador', default=False)
    is_active = models.BooleanField('Ativo', default=True)
    precisa_definir_senha = models.BooleanField(
        'Precisa definir senha (primeiro acesso)',
        default=False,
        help_text='True enquanto o usuário ainda não definiu a própria senha.',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    USERNAME_FIELD = 'matricula'
    REQUIRED_FIELDS = ['nome']

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.matricula})"

    @property
    def is_staff(self):
        return self.is_admin

    def definir_senha(self, senha):
        self.set_password(senha)
        self.precisa_definir_senha = False
        self.save(update_fields=['password', 'precisa_definir_senha', 'atualizado_em'])


class SolicitacaoRecuperacaoSenha(models.Model):
    """
    Fluxo de recuperação aprovado por administrador.
    O código em claro nunca é persistido — apenas o hash SHA-256.
    """

    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADA = 'aprovada', 'Aprovada'
        REJEITADA = 'rejeitada', 'Rejeitada'
        USADA = 'usada', 'Usada'
        EXPIRADA = 'expirada', 'Expirada'

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='recuperacoes_senha',
        verbose_name='Usuário',
    )
    matricula = models.CharField('Matrícula', max_length=50, db_index=True)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        db_index=True,
    )
    codigo_hash = models.CharField(
        'Hash do código',
        max_length=64,
        blank=True,
        default='',
        help_text='SHA-256 do código. Vazio até a aprovação.',
    )
    codigo_expira_em = models.DateTimeField('Código expira em', blank=True, null=True)
    tentativas_codigo = models.PositiveSmallIntegerField('Tentativas de código', default=0)
    solicitado_em = models.DateTimeField('Solicitado em', default=timezone.now, db_index=True)
    ip_origem = models.GenericIPAddressField('IP de origem', blank=True, null=True)
    admin_decisor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recuperacoes_decididas',
        verbose_name='Administrador decisório',
    )
    decidido_em = models.DateTimeField('Decidido em', blank=True, null=True)
    usado_em = models.DateTimeField('Usado em', blank=True, null=True)
    observacao_admin = models.CharField('Observação', max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Solicitação de recuperação de senha'
        verbose_name_plural = 'Solicitações de recuperação de senha'
        ordering = ['-solicitado_em']
        indexes = [
            models.Index(fields=['status', 'solicitado_em']),
            models.Index(fields=['matricula', 'status']),
        ]

    def __str__(self):
        return f'{self.matricula} · {self.status}'


class DocumentoCNH(models.Model):
    """Histórico de documentos de CNH enviados pelo usuário."""

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='documentos_cnh',
        verbose_name='Usuário',
    )
    data_validade = models.DateField(
        'Data de validade da CNH',
        blank=True,
        null=True,
        help_text='Preenchida pelo gestor no momento da aprovação.',
    )
    arquivo = models.FileField(
        'Arquivo da CNH',
        upload_to='cnh/%Y/%m/',
        help_text='PDF ou imagem do documento',
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
    )
    admin_aprovador = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name='cnh_decididas',
        blank=True,
        null=True,
        verbose_name='Administrador aprovador',
        limit_choices_to={'is_admin': True},
    )
    data_decisao = models.DateTimeField('Data da decisão', blank=True, null=True)
    observacao_admin = models.TextField('Observação do administrador', blank=True, null=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Documento de CNH'
        verbose_name_plural = 'Documentos de CNH'
        ordering = ['-criado_em']

    def __str__(self):
        return f"CNH #{self.id} - {self.usuario.nome} ({self.get_status_display()})"

    @property
    def esta_vencida(self):
        if not self.data_validade:
            return True
        return self.data_validade < timezone.localdate()

    @property
    def dias_restantes(self):
        if not self.data_validade:
            return None
        return (self.data_validade - timezone.localdate()).days

    @property
    def proxima_do_vencimento(self):
        dias = self.dias_restantes
        if dias is None:
            return False
        return 0 <= dias <= CNH_DIAS_ALERTA_VENCIMENTO

    def aprovar(self, admin_user, data_validade, observacao=None):
        self.status = 'aprovado'
        self.data_validade = data_validade
        self.admin_aprovador = admin_user
        self.data_decisao = timezone.now()
        if observacao is not None:
            self.observacao_admin = observacao
        self.save()

    def rejeitar(self, admin_user, observacao=None):
        self.status = 'rejeitado'
        self.admin_aprovador = admin_user
        self.data_decisao = timezone.now()
        if observacao is not None:
            self.observacao_admin = observacao
        self.save()


def cnh_vigente(usuario):
    """CNH aprovada com data de validade informada e ainda dentro da validade."""
    hoje = timezone.localdate()
    return (
        DocumentoCNH.objects
        .filter(
            usuario=usuario,
            status='aprovado',
            data_validade__isnull=False,
            data_validade__gte=hoje,
        )
        .order_by('-data_validade', '-data_decisao', '-id')
        .first()
    )


def cnh_pendente(usuario):
    return (
        DocumentoCNH.objects
        .filter(usuario=usuario, status='pendente')
        .order_by('-criado_em')
        .first()
    )


def usuario_pode_reservar_com_cnh(usuario):
    """True somente se existe CNH aprovada e não vencida."""
    return cnh_vigente(usuario) is not None


def resumo_cnh_usuario(usuario):
    """
    Situação consolidada da CNH para API/frontend.

    situacao:
      - sem_cnh
      - pendente
      - aprovada
      - proxima_vencimento
      - vencida
      - rejeitada (última rejeitada e sem vigente)
    """
    vigente = cnh_vigente(usuario)
    pendente = cnh_pendente(usuario)
    ultima = (
        DocumentoCNH.objects
        .filter(usuario=usuario)
        .order_by('-criado_em')
        .first()
    )

    if vigente:
        situacao = 'proxima_vencimento' if vigente.proxima_do_vencimento else 'aprovada'
        doc_ref = vigente
    elif pendente:
        situacao = 'pendente'
        doc_ref = pendente
    elif ultima and ultima.status == 'aprovado' and (ultima.esta_vencida or not ultima.data_validade):
        situacao = 'vencida'
        doc_ref = ultima
    elif ultima and ultima.status == 'rejeitado':
        situacao = 'rejeitada'
        doc_ref = ultima
    else:
        situacao = 'sem_cnh'
        doc_ref = None

    return {
        'situacao': situacao,
        'pode_reservar': vigente is not None,
        'vigente_id': vigente.id if vigente else None,
        'pendente_id': pendente.id if pendente else None,
        'data_validade': doc_ref.data_validade if doc_ref else None,
        'dias_restantes': doc_ref.dias_restantes if doc_ref and doc_ref.status == 'aprovado' else None,
        'proxima_do_vencimento': bool(vigente and vigente.proxima_do_vencimento),
        'mensagem': _mensagem_cnh(situacao, vigente, pendente),
    }


def _mensagem_cnh(situacao, vigente, pendente):
    if situacao == 'aprovada':
        return 'CNH válida e aprovada.'
    if situacao == 'proxima_vencimento':
        return (
            f'CNH válida, mas próxima do vencimento '
            f'({vigente.dias_restantes} dia(s) restantes).'
        )
    if situacao == 'pendente':
        if vigente:
            return 'Há uma nova CNH aguardando aprovação do gestor.'
        return (
            'CNH aguardando aprovação do gestor. '
            'Você não pode realizar reservas até a aprovação.'
        )
    if situacao == 'vencida':
        return (
            'CNH vencida. Envie uma nova CNH para voltar a realizar reservas.'
        )
    if situacao == 'rejeitada':
        return 'Última CNH foi rejeitada. Envie um novo documento.'
    return 'Nenhuma CNH cadastrada. Envie sua CNH para poder reservar veículos.'
