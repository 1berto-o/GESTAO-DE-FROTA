"""Recuperação de senha com aprovação administrativa e código de uso único."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

Usuario = get_user_model()

MSG_SOLICITACAO_OK = (
    'Se a matrícula estiver cadastrada, a solicitação foi registrada. '
    'Aguarde o administrador fornecer o código de recuperação.'
)
MSG_CODIGO_INVALIDO = 'Código inválido, expirado ou já utilizado.'
MSG_LIMITE_TENTATIVAS = 'Número máximo de tentativas excedido. Solicite um novo código.'

CODIGO_TAMANHO = 10
CODIGO_ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
CODIGO_VALIDADE = timedelta(minutes=30)
COOLDOWN_SOLICITACAO = timedelta(minutes=15)
LIMITE_SOLICITACOES_IP_HORA = 10
MAX_TENTATIVAS_CODIGO = 5


def _normalizar_matricula(matricula: str) -> str:
    from .validators import normalizar_matricula
    return normalizar_matricula(matricula)


def hash_codigo(codigo: str) -> str:
    material = f'{codigo.strip().upper()}|{settings.SECRET_KEY}'.encode('utf-8')
    return hashlib.sha256(material).hexdigest()


def gerar_codigo() -> str:
    return ''.join(secrets.choice(CODIGO_ALFABETO) for _ in range(CODIGO_TAMANHO))


def codigo_confere(codigo: str, codigo_hash: str) -> bool:
    if not codigo or not codigo_hash:
        return False
    return hmac.compare_digest(hash_codigo(codigo), codigo_hash)


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
    return forwarded or request.META.get('REMOTE_ADDR') or None


def _rate_limit_ip(ip: str | None) -> bool:
    """Retorna True se o IP excedeu o limite (deve ser bloqueado)."""
    if not ip:
        return False
    from .models import SolicitacaoRecuperacaoSenha

    desde = timezone.now() - timedelta(hours=1)
    total = SolicitacaoRecuperacaoSenha.objects.filter(
        ip_origem=ip, solicitado_em__gte=desde,
    ).count()
    return total >= LIMITE_SOLICITACOES_IP_HORA


def solicitar_recuperacao(*, matricula: str, request=None):
    """
    Registra solicitação pendente quando possível.
    Sempre retorna a mesma mensagem genérica (anti-enumeração).
    """
    from .models import SolicitacaoRecuperacaoSenha

    matricula_n = _normalizar_matricula(matricula)
    ip = _client_ip(request)

    if not matricula_n or _rate_limit_ip(ip):
        return {'detail': MSG_SOLICITACAO_OK}

    usuario = Usuario.objects.filter(matricula=matricula_n).first()
    if not usuario or not usuario.is_active:
        return {'detail': MSG_SOLICITACAO_OK}

    agora = timezone.now()
    recente = SolicitacaoRecuperacaoSenha.objects.filter(
        usuario=usuario,
        status=SolicitacaoRecuperacaoSenha.Status.PENDENTE,
        solicitado_em__gte=agora - COOLDOWN_SOLICITACAO,
    ).exists()
    if recente:
        return {'detail': MSG_SOLICITACAO_OK}

    # Cancela pedidos pendentes antigos do mesmo usuário.
    SolicitacaoRecuperacaoSenha.objects.filter(
        usuario=usuario,
        status=SolicitacaoRecuperacaoSenha.Status.PENDENTE,
    ).update(status=SolicitacaoRecuperacaoSenha.Status.EXPIRADA)

    criada = SolicitacaoRecuperacaoSenha.objects.create(
        usuario=usuario,
        matricula=usuario.matricula,
        status=SolicitacaoRecuperacaoSenha.Status.PENDENTE,
        ip_origem=ip,
        solicitado_em=agora,
    )
    return {'detail': MSG_SOLICITACAO_OK, '_criada': criada}


@transaction.atomic
def aprovar_solicitacao(*, solicitacao, admin):
    from .models import SolicitacaoRecuperacaoSenha

    if solicitacao.status != SolicitacaoRecuperacaoSenha.Status.PENDENTE:
        raise ValueError('Somente solicitações pendentes podem ser aprovadas.')

    # Invalida códigos aprovados ainda não usados do mesmo usuário.
    SolicitacaoRecuperacaoSenha.objects.filter(
        usuario=solicitacao.usuario,
        status=SolicitacaoRecuperacaoSenha.Status.APROVADA,
    ).exclude(pk=solicitacao.pk).update(
        status=SolicitacaoRecuperacaoSenha.Status.EXPIRADA,
    )

    codigo = gerar_codigo()
    agora = timezone.now()
    solicitacao.status = SolicitacaoRecuperacaoSenha.Status.APROVADA
    solicitacao.codigo_hash = hash_codigo(codigo)
    solicitacao.codigo_expira_em = agora + CODIGO_VALIDADE
    solicitacao.tentativas_codigo = 0
    solicitacao.admin_decisor = admin
    solicitacao.decidido_em = agora
    solicitacao.save(update_fields=[
        'status', 'codigo_hash', 'codigo_expira_em', 'tentativas_codigo',
        'admin_decisor', 'decidido_em',
    ])
    return codigo


@transaction.atomic
def rejeitar_solicitacao(*, solicitacao, admin, observacao=''):
    from .models import SolicitacaoRecuperacaoSenha

    if solicitacao.status != SolicitacaoRecuperacaoSenha.Status.PENDENTE:
        raise ValueError('Somente solicitações pendentes podem ser rejeitadas.')

    solicitacao.status = SolicitacaoRecuperacaoSenha.Status.REJEITADA
    solicitacao.admin_decisor = admin
    solicitacao.decidido_em = timezone.now()
    solicitacao.observacao_admin = (observacao or '')[:255]
    solicitacao.codigo_hash = ''
    solicitacao.codigo_expira_em = None
    solicitacao.save(update_fields=[
        'status', 'admin_decisor', 'decidido_em', 'observacao_admin',
        'codigo_hash', 'codigo_expira_em',
    ])


def _invalidar_tokens(usuario):
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
    except Exception:
        return
    for token in OutstandingToken.objects.filter(user=usuario):
        BlacklistedToken.objects.get_or_create(token=token)


def redefinir_com_codigo(*, matricula: str, codigo: str, password: str):
    """
    Valida o código e redefine a senha.
    Contadores de tentativa e marcações de expiração são commitados
    mesmo quando a operação falha (não podem ficar dentro de um
    atomic que dá rollback no raise).
    """
    from .models import SolicitacaoRecuperacaoSenha

    matricula_n = _normalizar_matricula(matricula)
    codigo_n = (codigo or '').strip().upper()
    if not matricula_n or not codigo_n:
        raise ValueError(MSG_CODIGO_INVALIDO)

    erro = None
    usuario_ok = None

    with transaction.atomic():
        solicitacao = (
            SolicitacaoRecuperacaoSenha.objects.select_for_update()
            .filter(
                matricula=matricula_n,
                status=SolicitacaoRecuperacaoSenha.Status.APROVADA,
            )
            .order_by('-decidido_em', '-solicitado_em')
            .first()
        )
        if not solicitacao:
            erro = MSG_CODIGO_INVALIDO
        elif solicitacao.tentativas_codigo >= MAX_TENTATIVAS_CODIGO:
            solicitacao.status = SolicitacaoRecuperacaoSenha.Status.EXPIRADA
            solicitacao.save(update_fields=['status'])
            erro = MSG_LIMITE_TENTATIVAS
        elif (
            not solicitacao.codigo_expira_em
            or solicitacao.codigo_expira_em < timezone.now()
        ):
            solicitacao.status = SolicitacaoRecuperacaoSenha.Status.EXPIRADA
            solicitacao.save(update_fields=['status'])
            erro = MSG_CODIGO_INVALIDO
        elif not codigo_confere(codigo_n, solicitacao.codigo_hash):
            solicitacao.tentativas_codigo += 1
            campos = ['tentativas_codigo']
            if solicitacao.tentativas_codigo >= MAX_TENTATIVAS_CODIGO:
                solicitacao.status = SolicitacaoRecuperacaoSenha.Status.EXPIRADA
                campos.append('status')
                erro = MSG_LIMITE_TENTATIVAS
            else:
                erro = MSG_CODIGO_INVALIDO
            solicitacao.save(update_fields=campos)
        else:
            usuario = solicitacao.usuario
            usuario.definir_senha(password)
            solicitacao.status = SolicitacaoRecuperacaoSenha.Status.USADA
            solicitacao.usado_em = timezone.now()
            solicitacao.codigo_hash = ''
            solicitacao.save(update_fields=['status', 'usado_em', 'codigo_hash'])
            _invalidar_tokens(usuario)
            usuario_ok = usuario

    if erro:
        raise ValueError(erro)
    return usuario_ok
