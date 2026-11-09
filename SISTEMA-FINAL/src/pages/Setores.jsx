import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import Modal from '../components/Modal'
import { useFeedback } from '../context/FeedbackContext'
import { errosParaFormulario, mensagemErroApi, textoCampo } from '../utils/erros'
import { formatDateTime } from '../utils/format'

const empty = { nome: '', descricao: '', ativo: true }

export default function Setores() {
  const feedback = useFeedback()
  const [itens, setItens] = useState([])
  const [loading, setLoading] = useState(true)
  const [busca, setBusca] = useState('')
  const [mostrarInativos, setMostrarInativos] = useState(true)
  const [formAberto, setFormAberto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState(empty)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const [detalhe, setDetalhe] = useState(null)
  const [membros, setMembros] = useState([])
  const [carregandoMembros, setCarregandoMembros] = useState(false)
  const [selecionados, setSelecionados] = useState([])
  const [destinoId, setDestinoId] = useState('')
  const [transferindo, setTransferindo] = useState(false)

  async function load(silencioso = false) {
    if (!silencioso) setLoading(true)
    try {
      const params = {}
      if (busca.trim()) params.q = busca.trim()
      if (!mostrarInativos) params.ativo = true
      const { data } = await api.get('/usuarios/setores/', { params })
      setItens(data.results ?? data)
    } catch (err) {
      if (!silencioso) {
        setItens([])
        feedback.erro(mensagemErroApi(err, 'Não foi possível carregar os setores.'))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [mostrarInativos])

  function abrirCriar() {
    setEditando(null)
    setForm(empty)
    setErrors({})
    setFormAberto(true)
  }

  function abrirEditar(setor) {
    setEditando(setor)
    setForm({
      nome: setor.nome || '',
      descricao: setor.descricao || '',
      ativo: Boolean(setor.ativo),
    })
    setErrors({})
    setFormAberto(true)
  }

  async function abrirMembros(setor) {
    setDetalhe(setor)
    setSelecionados([])
    setDestinoId('')
    setCarregandoMembros(true)
    try {
      const { data } = await api.get(`/usuarios/setores/${setor.id}/usuarios/`)
      setDetalhe(data.setor)
      setMembros(data.usuarios || [])
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível carregar os usuários do setor.'))
      setDetalhe(null)
      setMembros([])
    } finally {
      setCarregandoMembros(false)
    }
  }

  async function salvar(e) {
    e.preventDefault()
    setErrors({})
    setSaving(true)
    try {
      if (editando) {
        await api.patch(`/usuarios/setores/${editando.id}/`, form)
        feedback.sucesso('Setor atualizado.')
      } else {
        await api.post('/usuarios/setores/', form)
        feedback.sucesso('Setor cadastrado.')
      }
      setFormAberto(false)
      await load()
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível salvar o setor.'))
    } finally {
      setSaving(false)
    }
  }

  async function alternarAtivo(setor) {
    const ativar = !setor.ativo
    if (!ativar && (setor.usuarios_ativos_count ?? 0) > 0) {
      feedback.atencao(
        `Há ${setor.usuarios_ativos_count} usuário(s) ativo(s) neste setor. ` +
          'Abra “Membros” para transferir ou remover o vínculo antes de desativar.',
      )
      await abrirMembros(setor)
      return
    }
    const ok = await feedback.confirmar({
      titulo: ativar ? 'Ativar setor' : 'Desativar setor',
      mensagem: ativar
        ? `Ativar o setor "${setor.nome}"?`
        : `Desativar "${setor.nome}"? Usuários inativos podem permanecer vinculados; o setor deixa de aparecer para novos vínculos.`,
      confirmar: ativar ? 'Ativar' : 'Desativar',
      tom: ativar ? 'primary' : 'danger',
    })
    if (!ok) return
    try {
      await api.patch(`/usuarios/setores/${setor.id}/`, { ativo: ativar })
      feedback.sucesso(ativar ? 'Setor ativado.' : 'Setor desativado.')
      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível alterar o status.'))
    }
  }

  function toggleSelecionado(id) {
    setSelecionados((atual) =>
      atual.includes(id) ? atual.filter((x) => x !== id) : [...atual, id],
    )
  }

  function selecionarTodosAtivos() {
    const ids = membros.filter((u) => u.is_active).map((u) => u.id)
    setSelecionados(ids)
  }

  async function transferir(removerVinculo) {
    if (!detalhe || selecionados.length === 0) {
      feedback.atencao('Selecione ao menos um usuário.')
      return
    }
    const destino = removerVinculo ? null : (destinoId === '' ? null : Number(destinoId))
    if (!removerVinculo && !destino) {
      feedback.atencao('Escolha o setor de destino ou remova o vínculo.')
      return
    }
    const ok = await feedback.confirmar({
      titulo: removerVinculo ? 'Remover vínculo' : 'Transferir usuários',
      mensagem: removerVinculo
        ? `Remover o setor de ${selecionados.length} usuário(s)? As contas permanecem ativas.`
        : `Transferir ${selecionados.length} usuário(s) para o setor selecionado?`,
      confirmar: removerVinculo ? 'Remover vínculo' : 'Transferir',
      tom: removerVinculo ? 'danger' : 'primary',
    })
    if (!ok) return
    setTransferindo(true)
    try {
      const { data } = await api.post(`/usuarios/setores/${detalhe.id}/transferir/`, {
        usuario_ids: selecionados,
        setor_destino_id: destino,
      })
      feedback.sucesso(
        removerVinculo
          ? `${data.atualizados} vínculo(s) removido(s).`
          : `${data.atualizados} usuário(s) transferido(s).`,
      )
      setDetalhe(data.setor)
      setSelecionados([])
      setDestinoId('')
      const membrosResp = await api.get(`/usuarios/setores/${detalhe.id}/usuarios/`)
      setMembros(membrosResp.data.usuarios || [])
      await load(true)
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível atualizar os vínculos.'))
    } finally {
      setTransferindo(false)
    }
  }

  const erroGeral = textoCampo(errors, 'non_field_errors') || textoCampo(errors, 'detail') || textoCampo(errors, 'ativo')
  const destinos = itens.filter((s) => s.ativo && s.id !== detalhe?.id)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Setores</h1>
          <p className="muted-note">
            Cadastro administrativo para vínculo de usuários. A desativação só é permitida quando
            não houver usuários ativos no setor.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={abrirCriar}>
          Novo setor
        </button>
      </div>

      <div className="toolbar-row">
        <form
          className="search-inline"
          onSubmit={(e) => {
            e.preventDefault()
            load()
          }}
        >
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Pesquisar por nome ou descrição"
            aria-label="Pesquisar setores"
          />
          <button type="submit" className="btn btn-ghost">
            Buscar
          </button>
        </form>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={mostrarInativos}
            onChange={(e) => setMostrarInativos(e.target.checked)}
          />
          <span>Incluir inativos</span>
        </label>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : itens.length === 0 ? (
        <EmptyState icon="◉" title="Nenhum setor encontrado" />
      ) : (
        <>
          <div className="table-desktop-only table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Descrição</th>
                  <th>Ativos</th>
                  <th>Inativos</th>
                  <th>Status</th>
                  <th>Atualizado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {itens.map((s) => (
                  <tr key={s.id} className={s.ativo ? '' : 'row-inactive'}>
                    <td>
                      <strong>{s.nome}</strong>
                    </td>
                    <td>{s.descricao || '—'}</td>
                    <td>{s.usuarios_ativos_count ?? 0}</td>
                    <td>{s.usuarios_inativos_count ?? 0}</td>
                    <td>
                      <span className={`chip ${s.ativo ? 'chip-disponivel' : 'chip-inativo'}`}>
                        {s.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td>{formatDateTime(s.atualizado_em)}</td>
                    <td className="table-actions">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => abrirMembros(s)}
                      >
                        Membros
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => abrirEditar(s)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => alternarAtivo(s)}
                      >
                        {s.ativo ? 'Desativar' : 'Ativar'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mobile-card-list">
            {itens.map((s) => (
              <article key={s.id} className={`mobile-entity-card ${s.ativo ? '' : 'row-inactive'}`}>
                <div className="mobile-entity-card-head">
                  <div>
                    <strong>{s.nome}</strong>
                    <p className="muted-note">{s.descricao || 'Sem descrição'}</p>
                  </div>
                  <span className={`chip ${s.ativo ? 'chip-disponivel' : 'chip-inativo'}`}>
                    {s.ativo ? 'Ativo' : 'Inativo'}
                  </span>
                </div>
                <p className="muted-note">
                  {s.usuarios_ativos_count ?? 0} ativo(s) · {s.usuarios_inativos_count ?? 0}{' '}
                  inativo(s)
                </p>
                <div className="reservation-actions">
                  <button type="button" className="btn btn-ghost btn-touch" onClick={() => abrirMembros(s)}>
                    Membros
                  </button>
                  <button type="button" className="btn btn-ghost btn-touch" onClick={() => abrirEditar(s)}>
                    Editar
                  </button>
                  <button type="button" className="btn btn-ghost btn-touch" onClick={() => alternarAtivo(s)}>
                    {s.ativo ? 'Desativar' : 'Ativar'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {formAberto && (
        <Modal
          title={editando ? 'Editar setor' : 'Novo setor'}
          onClose={() => setFormAberto(false)}
          width={480}
        >
          <form className="form-grid" onSubmit={salvar}>
            <label className="field">
              <span>Nome</span>
              <input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                maxLength={100}
                autoFocus
              />
              {textoCampo(errors, 'nome') && (
                <small className="field-error">{textoCampo(errors, 'nome')}</small>
              )}
            </label>
            <label className="field">
              <span>Descrição (opcional)</span>
              <textarea
                rows={3}
                value={form.descricao}
                onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
              />
            </label>
            {editando && (
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={form.ativo}
                  onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))}
                />
                <span>Setor ativo</span>
              </label>
            )}
            {erroGeral && <div className="form-error">{erroGeral}</div>}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setFormAberto(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Salvando…' : 'Salvar'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {detalhe && (
        <Modal title={`Membros — ${detalhe.nome}`} onClose={() => setDetalhe(null)} width={640}>
          {carregandoMembros ? (
            <div className="skeleton-list" />
          ) : (
            <>
              <p className="muted-note">
                Ativos: {detalhe.usuarios_ativos_count ?? 0} · Inativos:{' '}
                {detalhe.usuarios_inativos_count ?? 0}. Transfira ou remova o vínculo dos ativos
                antes de desativar o setor.
              </p>
              {membros.length === 0 ? (
                <EmptyState icon="◉" title="Nenhum usuário vinculado" />
              ) : (
                <div className="table-scroll" style={{ maxHeight: 280 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th></th>
                        <th>Nome</th>
                        <th>Matrícula</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {membros.map((u) => (
                        <tr key={u.id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={selecionados.includes(u.id)}
                              onChange={() => toggleSelecionado(u.id)}
                              aria-label={`Selecionar ${u.nome}`}
                            />
                          </td>
                          <td>{u.nome}</td>
                          <td>{u.matricula}</td>
                          <td>
                            <span className={`chip ${u.is_active ? 'chip-disponivel' : 'chip-inativo'}`}>
                              {u.is_active ? 'Ativo' : 'Inativo'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="toolbar-row" style={{ marginTop: 12 }}>
                <button type="button" className="btn btn-ghost btn-sm" onClick={selecionarTodosAtivos}>
                  Selecionar ativos
                </button>
                <label className="field" style={{ flex: 1, margin: 0 }}>
                  <span className="sr-only">Setor de destino</span>
                  <select
                    value={destinoId}
                    onChange={(e) => setDestinoId(e.target.value)}
                    aria-label="Setor de destino"
                  >
                    <option value="">Transferir para…</option>
                    {destinos.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.nome}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={transferindo || selecionados.length === 0}
                  onClick={() => transferir(true)}
                >
                  Remover vínculo
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={transferindo || selecionados.length === 0 || !destinoId}
                  onClick={() => transferir(false)}
                >
                  {transferindo ? 'Aplicando…' : 'Transferir'}
                </button>
              </div>
            </>
          )}
        </Modal>
      )}
    </div>
  )
}
