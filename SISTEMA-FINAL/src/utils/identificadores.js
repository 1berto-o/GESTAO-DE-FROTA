/**
 * Regras de identificação alinhadas ao backend (usuarios.validators).
 *
 * Matrícula: apenas dígitos, 1–50 caracteres; zeros à esquerda preservados.
 * Telefone: dígitos com DDI opcional; 10–13 dígitos após normalizar.
 */

export const MATRICULA_MAX = 50
export const MATRICULA_MSG =
  'A matrícula deve conter apenas números (0-9), sem letras, espaços ou símbolos.'

export const TELEFONE_MSG =
  'Informe um telefone válido com DDD (apenas números). Ex.: (11) 98765-4321'

export function normalizarMatricula(valor) {
  return String(valor ?? '').trim()
}

export function filtrarDigitosMatricula(valor) {
  return String(valor ?? '').replace(/\D/g, '').slice(0, MATRICULA_MAX)
}

export function matriculaEValida(valor) {
  const m = normalizarMatricula(valor)
  return /^\d{1,50}$/.test(m)
}

export function normalizarTelefoneDigitos(valor) {
  const bruto = String(valor ?? '').trim()
  if (!bruto) return ''
  const temMais = bruto.startsWith('+')
  const digitos = bruto.replace(/\D/g, '')
  if (!digitos) return ''
  return temMais ? `+${digitos}` : digitos
}

export function telefoneEValido(valor) {
  const bruto = String(valor ?? '').trim()
  if (!bruto) return true
  if (!/^[\d\s().+-]+$/.test(bruto)) return false
  const digitos = bruto.replace(/\D/g, '')
  return digitos.length >= 10 && digitos.length <= 13
}

/** Máscara visual BR: (11) 98765-4321 ou (11) 3456-7890 */
export function formatarTelefoneExibicao(valor) {
  const digitos = String(valor ?? '').replace(/\D/g, '').slice(0, 13)
  if (!digitos) return ''
  let d = digitos
  if (d.startsWith('55') && d.length > 11) {
    d = d.slice(2)
  }
  d = d.slice(0, 11)
  if (d.length <= 2) return d.length ? `(${d}` : ''
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) {
    return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  }
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
}
