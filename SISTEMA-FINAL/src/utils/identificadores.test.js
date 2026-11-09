import test from 'node:test'
import assert from 'node:assert/strict'
import {
  filtrarDigitosMatricula,
  formatarTelefoneExibicao,
  matriculaEValida,
  normalizarMatricula,
  normalizarTelefoneDigitos,
  telefoneEValido,
} from './identificadores.js'

test('matrícula aceita só dígitos e preserva zeros', () => {
  assert.equal(normalizarMatricula(' 0123 '), '0123')
  assert.equal(filtrarDigitosMatricula('a0b1c2'), '012')
  assert.equal(matriculaEValida('012345'), true)
  assert.equal(matriculaEValida('012345') && '012345' !== '12345', true)
  assert.equal(matriculaEValida('ABC'), false)
  assert.equal(matriculaEValida('12-34'), false)
  assert.equal(matriculaEValida(''), false)
})

test('telefone normaliza e valida', () => {
  assert.equal(normalizarTelefoneDigitos('(11) 98765-4321'), '11987654321')
  assert.equal(telefoneEValido('11987654321'), true)
  assert.equal(telefoneEValido('123'), false)
  assert.equal(telefoneEValido(''), true)
  assert.equal(formatarTelefoneExibicao('11987654321'), '(11) 98765-4321')
})
