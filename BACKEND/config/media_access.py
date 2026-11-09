"""
Acesso controlado a arquivos em MEDIA_ROOT.

O Nginx não serve /media/ diretamente. A rota Django exige:
- token assinado de curta duração (?t=...), emitido após checagem de permissão; ou
- JWT Bearer de usuário autenticado, com nova checagem por prefixo/objeto.

Previne path traversal e download anônimo de CNH, termos e vistorias.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils.http import urlencode
from django.views import View
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

_SALT = 'fleetops.media.v1'
_DEFAULT_MAX_AGE = 3600  # 1 hora


def _max_age() -> int:
    return int(getattr(settings, 'MEDIA_URL_TOKEN_MAX_AGE', _DEFAULT_MAX_AGE))


def _signer() -> signing.TimestampSigner:
    return signing.TimestampSigner(salt=_SALT)


def normalizar_caminho_relativo(path: str) -> str:
    """Normaliza e rejeita path traversal / absoluto."""
    bruto = (path or '').replace('\\', '/').lstrip('/')
    if not bruto or bruto.startswith('../') or '/../' in f'/{bruto}/' or '..' in PurePosixPath(bruto).parts:
        raise ValueError('Caminho de mídia inválido.')
    puro = PurePosixPath(bruto)
    if puro.is_absolute() or any(p in ('', '.') for p in puro.parts):
        # '.' isolado ou vazio
        if any(p == '' for p in puro.parts):
            raise ValueError('Caminho de mídia inválido.')
    return str(puro)


def caminho_absoluto_seguro(relativo: str) -> Path:
    relativo = normalizar_caminho_relativo(relativo)
    root = Path(settings.MEDIA_ROOT).resolve()
    alvo = (root / relativo).resolve()
    if not str(alvo).startswith(str(root) + '/') and alvo != root:
        raise ValueError('Caminho fora de MEDIA_ROOT.')
    if not alvo.is_file():
        raise FileNotFoundError(relativo)
    return alvo


def assinar_caminho(relativo: str) -> str:
    return _signer().sign(normalizar_caminho_relativo(relativo))


def verificar_token(token: str) -> str:
    return normalizar_caminho_relativo(
        _signer().unsign(token, max_age=_max_age())
    )


def url_midia_assinada(request, file_field) -> str | None:
    """Gera URL absoluta /media/<path>?t=<token> para um FileField/ImageField."""
    if not file_field or not request:
        return None
    try:
        name = file_field.name
    except Exception:
        return None
    if not name:
        return None
    try:
        relativo = normalizar_caminho_relativo(name)
    except ValueError:
        return None
    token = assinar_caminho(relativo)
    base = request.build_absolute_uri(settings.MEDIA_URL + relativo)
    sep = '&' if '?' in base else '?'
    return f'{base}{sep}{urlencode({"t": token})}'


def usuario_pode_acessar(user, relativo: str) -> bool:
    """Regras para acesso via JWT (sem token assinado)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_admin', False):
        return True

    prefix = relativo.split('/', 1)[0]
    if prefix == 'veiculos':
        return True

    if prefix == 'cnh':
        from usuarios.models import DocumentoCNH
        return DocumentoCNH.objects.filter(
            usuario_id=user.id, arquivo=relativo,
        ).exists()

    if prefix == 'termos':
        from termos.models import TermoResponsabilidade
        return TermoResponsabilidade.objects.filter(
            usuario_id=user.id, arquivo_pdf=relativo,
        ).exists()

    if prefix == 'vistorias':
        from vistorias.models import FotoVistoria
        return FotoVistoria.objects.filter(
            foto=relativo,
            vistoria__reserva__usuario_id=user.id,
        ).exists()

    return False


class ProtectedMediaView(View):
    """GET /media/<path> — token assinado ou JWT autenticado."""

    def get(self, request, path):
        token = request.GET.get('t') or request.GET.get('token')
        relativo = None

        if token:
            try:
                relativo = verificar_token(token)
            except signing.SignatureExpired:
                return HttpResponseForbidden('Link de mídia expirado.')
            except signing.BadSignature:
                return HttpResponseForbidden('Link de mídia inválido.')
            # Token assinado deve referir o mesmo path da URL
            try:
                path_norm = normalizar_caminho_relativo(path)
            except ValueError:
                raise Http404()
            if path_norm != relativo:
                return HttpResponseForbidden('Link de mídia inválido.')
        else:
            user = None
            try:
                auth = JWTAuthentication().authenticate(request)
                if auth:
                    user = auth[0]
            except (InvalidToken, AuthenticationFailed):
                user = None
            try:
                relativo = normalizar_caminho_relativo(path)
            except ValueError:
                raise Http404()
            if not usuario_pode_acessar(user, relativo):
                return HttpResponseForbidden(
                    'Autenticação necessária para acessar este arquivo.'
                )

        try:
            arquivo = caminho_absoluto_seguro(relativo)
        except (ValueError, FileNotFoundError):
            raise Http404()

        content_type, _ = mimetypes.guess_type(str(arquivo))
        response = FileResponse(arquivo.open('rb'), content_type=content_type or 'application/octet-stream')
        response['Content-Disposition'] = f'inline; filename="{arquivo.name}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response
