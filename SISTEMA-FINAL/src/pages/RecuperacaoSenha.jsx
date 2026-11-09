import { useEffect, useState } from 'react'
import { KeyRound, Copy, Check } from 'lucide-react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import { formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

const FILTROS = [
  { id: 'pendente', label: 'Pendentes' },
  { id: 'aprovada', label: 'Aprovadas' },
  { id: 'rejeitada', label: 'Rejeitadas' },
  { id: 'usada', label: 'Usadas' },
  { id: 'todas', label: 'Todas' },
]

export default function RecuperacaoSenha() {
  const feedback = useFeedback()
  const [filtro, setFiltro] = useState('pendente')
  const [itens, setItens] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [codigoExibido, setCodigoExibido] = useState(null)
  const [copiado, setCopiado] = useState(false)

  async function load(silencioso = false) {
    if (!silencioso) setLoading(true)
    try {
      const { data } = await api.get('/usuarios/recuperacao-senha/', {
        params: { status: filtro },
      })
      setItens(data.results ?? data)
    } catch (err) {
      if (!silencioso) {
        setItens([])
        feedback.erro(mensagemErroApi(err, 'Não foi possível carregar as solicitações.'))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(() => load(true), 30000)
    return () => clearInterval(id)
  }, [filtro])

  async function aprovar(item) {
    const ok = await feedback.confirmar({
      titulo: 'Aprovar recuperação',
      mensagem: `Gerar código de uso único para ${item.usuario_nome} (${item.matricula})? O código será exibido apenas uma vez.`,
      confirmar: 'Aprovar e gerar código',
    })
    if (!ok) return
    setProcessando(item.id)
    try {
      const { data } = await api.post(`/usuarios/recuperacao-senha/${item.id}/aprovar/`)
      setCodigoExibido({
        codigo: data.codigo,
        matricula: data.matricula,
        nome: data.usuario_nome,
        expira_em: data.expira_em,
        aviso: data.aviso,
      })
      setCopiado(false)
      feedback.sucesso('Código gerado. Entregue-o ao usuário por canal confiável.')
      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível aprovar a solicitação.'))
    } finally {
      setProcessando(null)
    }
  }

  async function rejeitar(item) {
    const ok = await feedback.confirmar({
      titulo: 'Rejeitar solicitação',
      mensagem: `Rejeitar o pedido de ${item.usuario_nome} (${item.matricula})?`,
      confirmar: 'Rejeitar',
      cancelar: 'Voltar',
      tom: 'danger',
    })
    if (!ok) return
    setProcessando(item.id)
    try {
      await api.post(`/usuarios/recuperacao-senha/${item.id}/rejeitar/`, {
        observacao: '',
      })
      feedback.sucesso('Solicitação rejeitada.')
      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível rejeitar a solicitação.'))
    } finally {
      setProcessando(null)
    }
  }

  async function copiarCodigo() {
    if (!codigoExibido?.codigo) return
    try {
      await navigator.clipboard.writeText(codigoExibido.codigo)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      feedback.erro('Não foi possível copiar. Selecione o código manualmente.')
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Recuperação de senha</h1>
          <p className="muted-note">
            Solicitações dos usuários. Ao aprovar, um código de uso único é gerado e exibido uma
            única vez — entregue-o por canal confiável. Você não define a senha do usuário.
          </p>
        </div>
      </div>

      <div className="audit-tabs" role="tablist" aria-label="Filtro de status">
        {FILTROS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={filtro === f.id}
            className={`btn btn-sm ${filtro === f.id ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setFiltro(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {codigoExibido && (
        <div className="panel recovery-code-panel" role="status">
          <div className="recovery-code-head">
            <KeyRound size={20} strokeWidth={1.75} aria-hidden />
            <div>
              <strong>Código gerado (exibição única)</strong>
              <p className="muted-note">
                {codigoExibido.nome} · matrícula {codigoExibido.matricula}
                {codigoExibido.expira_em
                  ? ` · expira em ${formatDateTime(codigoExibido.expira_em)}`
                  : ''}
              </p>
            </div>
          </div>
          <div className="recovery-code-value">
            <code>{codigoExibido.codigo}</code>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={copiarCodigo}
              aria-label="Copiar código"
            >
              {copiado ? <Check size={16} aria-hidden /> : <Copy size={16} aria-hidden />}
              {copiado ? 'Copiado' : 'Copiar'}
            </button>
          </div>
          <p className="muted-note">
            {codigoExibido.aviso || 'Este código não será exibido novamente.'} Não armazene em
            sistemas inseguros.
          </p>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setCodigoExibido(null)}
          >
            Fechar aviso
          </button>
        </div>
      )}

      {loading ? (
        <div className="skeleton-list" />
      ) : itens.length === 0 ? (
        <EmptyState
          icon="◉"
          title={
            filtro === 'pendente'
              ? 'Nenhuma solicitação pendente'
              : 'Nenhuma solicitação neste filtro'
          }
        />
      ) : (
        <>
          <div className="table-desktop-only table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Usuário</th>
                  <th>Matrícula</th>
                  <th>Status</th>
                  <th>Solicitado em</th>
                  <th>Decisão</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item) => (
                  <tr key={item.id}>
                    <td>{item.usuario_nome}</td>
                    <td>{item.matricula}</td>
                    <td>
                      <span className="chip">{item.status}</span>
                    </td>
                    <td>{formatDateTime(item.solicitado_em)}</td>
                    <td>
                      {item.decidido_em
                        ? `${formatDateTime(item.decidido_em)}${
                            item.admin_decisor_nome ? ` · ${item.admin_decisor_nome}` : ''
                          }`
                        : '—'}
                    </td>
                    <td className="table-actions">
                      {item.status === 'pendente' && (
                        <>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            disabled={processando === item.id}
                            onClick={() => aprovar(item)}
                          >
                            Aprovar
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost-danger btn-sm"
                            disabled={processando === item.id}
                            onClick={() => rejeitar(item)}
                          >
                            Rejeitar
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mobile-card-list">
            {itens.map((item) => (
              <article key={item.id} className="mobile-entity-card">
                <div className="mobile-entity-card-head">
                  <div>
                    <strong>{item.usuario_nome}</strong>
                    <p className="muted-note">Matrícula {item.matricula}</p>
                  </div>
                  <span className="chip">{item.status}</span>
                </div>
                <p className="muted-note">Solicitado: {formatDateTime(item.solicitado_em)}</p>
                {item.status === 'pendente' && (
                  <div className="reservation-actions">
                    <button
                      type="button"
                      className="btn btn-primary btn-touch"
                      disabled={processando === item.id}
                      onClick={() => aprovar(item)}
                    >
                      Aprovar
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost-danger btn-touch"
                      disabled={processando === item.id}
                      onClick={() => rejeitar(item)}
                    >
                      Rejeitar
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
