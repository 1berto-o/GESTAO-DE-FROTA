"""
Validadores de identificação e contato.

Decisão — matrícula (2026-11-09):
- Identificador opaco armazenado como texto (CharField max_length=50).
- Apenas dígitos 0-9; sem letras, espaços ou símbolos.
- Comprimento: 1 a 50 (limite já existente no modelo; sem tamanho fixo inventado).
- Zeros à esquerda são significativos e devem ser preservados (nunca converter
  para inteiro).
- Normalização: somente strip de espaços nas extremidades.
"""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError

MATRICULA_MAX = 50
MATRICULA_PADRAO_MSG = (
    'A matrícula deve conter apenas números (0-9), sem letras, espaços '
    'ou símbolos. Zeros à esquerda são preservados.'
)

# Telefone BR: dígitos com DDI opcional; após normalizar, 10–13 dígitos.
TELEFONE_DIGITOS_MIN = 10
TELEFONE_DIGITOS_MAX = 13
TELEFONE_MSG = (
    'Informe um telefone válido com DDD (apenas números). '
    'Ex.: 11987654321 ou +5511987654321.'
)

_RE_APENAS_DIGITOS = re.compile(r'^\d+$')
_RE_TELEFONE_PERMITIDO = re.compile(r'^[\d\s().+-]+$')


def normalizar_matricula(valor: str | None) -> str:
    """Remove espaços nas extremidades; não altera zeros à esquerda."""
    return (valor or '').strip()


def matricula_e_valida(valor: str | None) -> bool:
    matricula = normalizar_matricula(valor)
    if not matricula or len(matricula) > MATRICULA_MAX:
        return False
    return bool(_RE_APENAS_DIGITOS.fullmatch(matricula))


def validar_matricula(valor: str | None) -> str:
    """
    Valida e devolve a matrícula normalizada (strip).
    Preserva zeros à esquerda.
    """
    matricula = normalizar_matricula(valor)
    if not matricula:
        raise ValidationError('Informe a matrícula.', code='required')
    if len(matricula) > MATRICULA_MAX:
        raise ValidationError(
            f'A matrícula deve ter no máximo {MATRICULA_MAX} dígitos.',
            code='max_length',
        )
    if not _RE_APENAS_DIGITOS.fullmatch(matricula):
        raise ValidationError(MATRICULA_PADRAO_MSG, code='invalid')
    return matricula


def normalizar_telefone(valor: str | None) -> str:
    """
    Mantém apenas dígitos e um '+' inicial opcional.
    Não aplica maiúsculas (telefone não é texto nominal).
    """
    bruto = (valor or '').strip()
    if not bruto:
        return ''
    tem_mais = bruto.startswith('+')
    digitos = re.sub(r'\D', '', bruto)
    if not digitos:
        return ''
    return f'+{digitos}' if tem_mais else digitos


def telefone_e_valido(valor: str | None) -> bool:
    """Vazio é válido (campo opcional)."""
    bruto = (valor or '').strip()
    if not bruto:
        return True
    if not _RE_TELEFONE_PERMITIDO.fullmatch(bruto):
        return False
    normalizado = normalizar_telefone(bruto)
    digitos = re.sub(r'\D', '', normalizado)
    return TELEFONE_DIGITOS_MIN <= len(digitos) <= TELEFONE_DIGITOS_MAX


def validar_telefone(valor: str | None) -> str:
    """Valida telefone opcional e devolve forma normalizada (dígitos / +dígitos)."""
    bruto = (valor or '').strip()
    if not bruto:
        return ''
    if not _RE_TELEFONE_PERMITIDO.fullmatch(bruto):
        raise ValidationError(TELEFONE_MSG, code='invalid')
    normalizado = normalizar_telefone(bruto)
    digitos = re.sub(r'\D', '', normalizado)
    if not (TELEFONE_DIGITOS_MIN <= len(digitos) <= TELEFONE_DIGITOS_MAX):
        raise ValidationError(TELEFONE_MSG, code='invalid')
    return normalizado
