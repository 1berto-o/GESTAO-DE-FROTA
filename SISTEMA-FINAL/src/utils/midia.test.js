import assert from 'node:assert/strict'
import { test } from 'node:test'

import { urlMidia } from './midia.js'

const ORIGEM = 'http://127.0.0.1:8080'

test('vazio e blobs não são alterados', () => {
  assert.equal(urlMidia(''), '')
  assert.equal(urlMidia(null), '')
  assert.equal(urlMidia('blob:http://127.0.0.1:8080/abc'), 'blob:http://127.0.0.1:8080/abc')
  assert.equal(urlMidia('data:image/png;base64,AAA'), 'data:image/png;base64,AAA')
})

test('URL absoluta sem porta passa a usar o origin atual', () => {
  assert.equal(
    urlMidia('http://127.0.0.1/media/veiculos/carro.png', ORIGEM),
    'http://127.0.0.1:8080/media/veiculos/carro.png',
  )
})

test('caminho relativo de mídia usa o origin atual', () => {
  assert.equal(
    urlMidia('/media/veiculos/carro.png', ORIGEM),
    'http://127.0.0.1:8080/media/veiculos/carro.png',
  )
})

test('URL já no origin correto permanece equivalente', () => {
  assert.equal(
    urlMidia('http://127.0.0.1:8080/media/veiculos/carro.png', ORIGEM),
    'http://127.0.0.1:8080/media/veiculos/carro.png',
  )
})

test('URL externa não é reescrita', () => {
  assert.equal(
    urlMidia('https://cdn.exemplo.test/foto.png', ORIGEM),
    'https://cdn.exemplo.test/foto.png',
  )
})
