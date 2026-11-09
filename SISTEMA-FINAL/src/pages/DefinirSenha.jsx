import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { errosParaFormulario, textoCampo } from '../utils/erros'
import BrandLogo from '../components/BrandLogo'
import PasswordField from '../components/PasswordField'

export default function DefinirSenha() {
  const { user, loadPerfil, logout } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    if (password !== passwordConfirm) {
      setErrors({ password_confirm: ['A confirmação não confere com a senha.'] })
      return
    }
    setSaving(true)
    try {
      await api.post('/usuarios/definir-senha/', {
        password,
        password_confirm: passwordConfirm,
      })
      await loadPerfil()
      navigate('/', { replace: true })
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível definir a senha.'))
    } finally {
      setSaving(false)
    }
  }

  const erroGeral = textoCampo(errors, 'non_field_errors') || textoCampo(errors, 'detail')

  return (
    <div className="login-screen fo-auth">
      <div className="fo-auth-stripes" aria-hidden="true" />
      <aside className="login-side" aria-label="Identidade FleetOps">
        <div className="login-side-content">
          <BrandLogo variant="vertical" className="login-brand-logo" />
          <p className="login-tagline">Defina sua senha para concluir o primeiro acesso.</p>
        </div>
      </aside>

      <div className="login-form-wrap">
        <form className="login-form fo-card-auth" onSubmit={handleSubmit}>
          <BrandLogo variant="horizontal" className="login-form-logo" />
          <div className="login-form-heading">
            <h2>Definir senha</h2>
            <p className="login-subtitle">
              Olá{user?.nome ? `, ${user.nome.split(' ')[0]}` : ''}. Crie uma senha segura para a
              matrícula <strong>{user?.matricula}</strong>.
            </p>
          </div>
          <p className="muted-note login-password-hint">
            A senha deve ter pelo menos 8 caracteres, não pode ser só números nem uma senha comum, e
            não deve se parecer com o nome ou a matrícula.
          </p>

          <PasswordField
            label="Nova senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoFocus
            autoComplete="new-password"
            error={textoCampo(errors, 'password')}
          />

          <PasswordField
            label="Confirmar senha"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            error={textoCampo(errors, 'password_confirm')}
          />

          {erroGeral && <div className="form-error">{erroGeral}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={saving}>
            {saving ? 'Salvando…' : 'Confirmar senha'}
          </button>

          <button
            type="button"
            className="btn btn-ghost btn-block"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            Sair
          </button>
        </form>
      </div>
    </div>
  )
}
