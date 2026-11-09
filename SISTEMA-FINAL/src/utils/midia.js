/**
 * Ajusta URLs de /media e /static devolvidas pela API para o origin atual.
 *
 * Atrás do Nginx, Django pode montar URLs absolutas com o hostname sem porta
 * (ex.: http://127.0.0.1/media/... enquanto o app está em :8080). O arquivo
 * existe no caminho /media/...; só o host/porta é que falha.
 */
export function urlMidia(url, origem = origemPadrao()) {
  if (!url) return ''
  if (url.startsWith('blob:') || url.startsWith('data:')) return url

  const base = (origem || '').replace(/\/$/, '')

  try {
    if (/^https?:\/\//i.test(url) || url.startsWith('//')) {
      const parsed = new URL(url, base || 'http://localhost')
      const caminho = `${parsed.pathname}${parsed.search}`
      if (!ehArquivoDaAplicacao(caminho)) return url
      return base ? `${base}${caminho}` : caminho
    }
  } catch {
    return url
  }

  if (ehArquivoDaAplicacao(url)) {
    return base ? `${base}${url}` : url
  }

  return url
}

function ehArquivoDaAplicacao(caminho) {
  return caminho.startsWith('/media/') || caminho.startsWith('/static/')
}

function origemPadrao() {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin
  }
  return ''
}
