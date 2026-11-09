import { useEffect, useState } from 'react'
import api from '../services/api'
import Modal from './Modal'
import { errosParaFormulario, textoCampo } from '../utils/erros'
import {
  filtrarDigitosMatricula,
  formatarTelefoneExibicao,
  matriculaEValida,
  MATRICULA_MSG,
  normalizarTelefoneDigitos,
  telefoneEValido,
  TELEFONE_MSG,
} from '../utils/identificadores'
import { useFeedback } from '../context/FeedbackContext'

const empty = {
  matricula: '',
  nome: '',
  email: '',
  telefone: '',
  setor: '',
  is_admin: false,
  is_active: true,
}

export default function UserFormModal({ usuario, onClose, onSaved }) {
  const feedback = useFeedback()
  const [form, setForm] = useState(
    usuario
      ? {
          ...empty,
          ...usuario,
          setor: usuario.setor || '',
          telefone: usuario.telefone || '',
        }
      : empty,
  )
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [setores, setSetores] = useState([])
  const [carregandoSetores, setCarregandoSetores] = useState(true)

  useEffect(() => {
    let cancelado = false
    async function carregarSetores() {
      setCarregandoSetores(true)
      try {
        const { data } = await api.get('/usuarios/setores/', { params: { ativo: true } })
        let lista = data.results ?? data
        // Mantém o setor atual na edição mesmo se estiver inativo.
        if (usuario?.setor && !lista.some((s) => s.id === usuario.setor)) {
          try {
            const atual = await api.get(`/usuarios/setores/${usuario.setor}/`)
            lista = [atual.data, ...lista]
          } catch {
            /* ignore */
          }
        }
        if (!cancelado) setSetores(lista)
      } catch (err) {
        if (!cancelado) {
          setSetores([])
          feedback.erro('Não foi possível carregar os setores cadastrados.')
        }
      } finally {
        if (!cancelado) setCarregandoSetores(false)
      }
    }
    carregarSetores()
    return () => {
      cancelado = true
    }
  }, [usuario, feedback])

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    if (!usuario && !matriculaEValida(form.matricula)) {
      setErrors({ matricula: [MATRICULA_MSG] })
      return
    }
    if (!telefoneEValido(form.telefone)) {
      setErrors({ telefone: [TELEFONE_MSG] })
      return
    }
    if (!setores.length && !form.setor) {
      // setor opcional; se não há setores, apenas avisa e permite salvar sem vínculo
    }
    setSaving(true)
    try {
      const telefone = normalizarTelefoneDigitos(form.telefone) || null
      const setor = form.setor === '' || form.setor == null ? null : Number(form.setor)
      if (usuario) {
        const { nome, email, is_active } = form
        await api.patch(`/usuarios/${usuario.id}/`, {
          nome,
          email,
          telefone,
          setor,
          is_active,
        })
        feedback.sucesso('Usuário atualizado.')
      } else {
        const { matricula, nome, email, is_admin, is_active } = form
        await api.post('/usuarios/', {
          matricula,
          nome,
          email,
          telefone,
          setor,
          is_admin,
          is_active,
        })
        feedback.sucesso('Usuário cadastrado. A senha será definida no primeiro acesso.')
      }
      onSaved()
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível salvar o usuário. Tente novamente.'))
    } finally {
      setSaving(false)
    }
  }

  const erroGeral = textoCampo(errors, 'non_field_errors') || textoCampo(errors, 'detail')
  const semSetoresAtivos = !carregandoSetores && setores.filter((s) => s.ativo !== false).length === 0

  return (
    <Modal title={usuario ? 'Editar usuário' : 'Novo usuário'} onClose={onClose} width={520}>
      <form onSubmit={handleSubmit} className="form-grid">
        <div className="field-row">
          <label className="field">
            <span>Matrícula</span>
            <input
              value={form.matricula}
              onChange={(e) => update('matricula', filtrarDigitosMatricula(e.target.value))}
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={50}
              placeholder="Somente números"
              required
              disabled={!!usuario}
            />
            {textoCampo(errors, 'matricula') && (
              <small className="field-error">{textoCampo(errors, 'matricula')}</small>
            )}
          </label>
          <label className="field">
            <span>Nome completo</span>
            <input value={form.nome} onChange={(e) => update('nome', e.target.value)} required />
            {textoCampo(errors, 'nome') && (
              <small className="field-error">{textoCampo(errors, 'nome')}</small>
            )}
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            <span>E-mail</span>
            <input
              type="email"
              value={form.email || ''}
              onChange={(e) => update('email', e.target.value)}
            />
            {textoCampo(errors, 'email') && (
              <small className="field-error">{textoCampo(errors, 'email')}</small>
            )}
          </label>
          <label className="field">
            <span>Telefone</span>
            <input
              type="tel"
              inputMode="tel"
              value={formatarTelefoneExibicao(form.telefone || '')}
              onChange={(e) => update('telefone', e.target.value.replace(/\D/g, '').slice(0, 13))}
              placeholder="(11) 98765-4321"
              maxLength={16}
            />
            {textoCampo(errors, 'telefone') && (
              <small className="field-error">{textoCampo(errors, 'telefone')}</small>
            )}
          </label>
        </div>

        <label className="field">
          <span>Setor</span>
          <select
            value={form.setor === null || form.setor === undefined ? '' : form.setor}
            onChange={(e) => update('setor', e.target.value === '' ? '' : Number(e.target.value))}
            disabled={carregandoSetores}
          >
            <option value="">Sem setor</option>
            {setores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nome}
                {s.ativo === false ? ' (inativo)' : ''}
              </option>
            ))}
          </select>
          {semSetoresAtivos && (
            <small className="field-error">
              Nenhum setor ativo cadastrado. Cadastre setores em Administração → Setores antes de
              vincular usuários.
            </small>
          )}
          {textoCampo(errors, 'setor') && (
            <small className="field-error">{textoCampo(errors, 'setor')}</small>
          )}
        </label>

        {!usuario && (
          <>
            <p className="muted-note">
              O próprio usuário cria a senha no primeiro acesso, usando a matrícula.
            </p>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => update('is_admin', e.target.checked)}
              />
              <span>Administrador</span>
            </label>
          </>
        )}

        {usuario && (
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => update('is_active', e.target.checked)}
            />
            <span>Conta ativa</span>
          </label>
        )}

        {erroGeral && <div className="form-error">{erroGeral}</div>}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving || carregandoSetores}>
            {saving ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
