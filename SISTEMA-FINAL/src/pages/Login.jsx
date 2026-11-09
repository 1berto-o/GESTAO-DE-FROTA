import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { mensagemErroApi, errosParaFormulario, textoCampo } from '../utils/erros'
import { filtrarDigitosMatricula, matriculaEValida, MATRICULA_MSG } from '../utils/identificadores'
import BrandLogo from '../components/BrandLogo'
import PasswordField from '../components/PasswordField'
import api from '../services/api'

const MODO_LOGIN = 'login'
const MODO_SOLICITAR = 'solicitar'
const MODO_REDEFINIR = 'redefinir'

function mensagemErroLogin(err, primeiroAcesso) {
  const status = err.response?.status
  if (status === 401 || status === 400) {
    return primeiroAcesso
      ? 'Não foi possível iniciar o primeiro acesso. Verifique a matrícula.'
      : 'Matrícula ou senha inválidas.'
  }
  return mensagemErroApi(err, 'Não foi possível concluir o login. Tente novamente.')
}

export default function Login() {
  const { login, user, precisaDefinirSenha, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [modo, setModo] = useState(MODO_LOGIN)
  const [matricula, setMatricula] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [codigo, setCodigo] = useState('')
  const [primeiroAcesso, setPrimeiroAcesso] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [sucesso, setSucesso] = useState('')
  const [loading, setLoading] = useState(false)
  const submittingRef = useRef(false)

  useEffect(() => {
    if (authLoading || !user) return
    navigate(precisaDefinirSenha ? '/definir-senha' : '/', { replace: true })
  }, [authLoading, user, precisaDefinirSenha, navigate])

  function limparFeedback() {
    setError('')
    setFieldErrors({})
    setSucesso('')
  }

  function irPara(proximo) {
    limparFeedback()
    setPassword('')
    setPasswordConfirm('')
    setCodigo('')
    setPrimeiroAcesso(false)
    setModo(proximo)
  }

  async function handleLogin(e) {
    e.preventDefault()
    if (submittingRef.current) return
    if (!matriculaEValida(matricula)) {
      setError(MATRICULA_MSG)
      return
    }
    submittingRef.current = true
    limparFeedback()
    setLoading(true)
    try {
      const result = await login(matricula, primeiroAcesso ? '' : password)
      if (!result?.perfil) {
        setError(
          'Login autenticado, mas não foi possível carregar o perfil. Tente novamente.'
        )
        setLoading(false)
        submittingRef.current = false
      }
    } catch (err) {
      setError(mensagemErroLogin(err, primeiroAcesso))
      setLoading(false)
      submittingRef.current = false
    }
  }

  async function handleSolicitar(e) {
    e.preventDefault()
    if (submittingRef.current) return
    if (!matriculaEValida(matricula)) {
      setError(MATRICULA_MSG)
      return
    }
    submittingRef.current = true
    limparFeedback()
    setLoading(true)
    try {
      const { data } = await api.post('/usuarios/recuperacao-senha/solicitar/', {
        matricula,
      })
      setSucesso(
        data?.detail ||
          'Se a matrícula estiver cadastrada, a solicitação foi registrada.'
      )
    } catch (err) {
      setError(mensagemErroApi(err, 'Não foi possível registrar a solicitação.'))
    } finally {
      setLoading(false)
      submittingRef.current = false
    }
  }

  async function handleRedefinir(e) {
    e.preventDefault()
    if (submittingRef.current) return
    if (!matriculaEValida(matricula)) {
      setError(MATRICULA_MSG)
      return
    }
    submittingRef.current = true
    limparFeedback()
    if (password !== passwordConfirm) {
      setFieldErrors({ password_confirm: ['A confirmação não confere com a senha.'] })
      submittingRef.current = false
      return
    }
    setLoading(true)
    try {
      const { data } = await api.post('/usuarios/recuperacao-senha/redefinir/', {
        matricula,
        codigo: codigo.trim().toUpperCase(),
        password,
        password_confirm: passwordConfirm,
      })
      setSucesso(data?.detail || 'Senha redefinida com sucesso. Faça login com a nova senha.')
      setPassword('')
      setPasswordConfirm('')
      setCodigo('')
      setModo(MODO_LOGIN)
    } catch (err) {
      const formErrors = errosParaFormulario(err, 'Não foi possível redefinir a senha.')
      setFieldErrors(formErrors)
      setError(
        textoCampo(formErrors, 'non_field_errors') ||
          textoCampo(formErrors, 'detail') ||
          mensagemErroApi(err, 'Não foi possível redefinir a senha.')
      )
    } finally {
      setLoading(false)
      submittingRef.current = false
    }
  }

  const titulo =
    modo === MODO_SOLICITAR
      ? 'Esqueci minha senha'
      : modo === MODO_REDEFINIR
        ? 'Redefinir senha'
        : primeiroAcesso
          ? 'Primeiro acesso'
          : 'Entrar'

  const subtitulo =
    modo === MODO_SOLICITAR
      ? 'Informe sua matrícula. Um administrador analisará o pedido e fornecerá um código de uso único.'
      : modo === MODO_REDEFINIR
        ? 'Use a matrícula, o código recebido do administrador e a nova senha.'
        : primeiroAcesso
          ? 'Informe apenas a matrícula cadastrada pelo administrador para criar sua senha.'
          : 'Faça login para continuar.'

  const onSubmit =
    modo === MODO_SOLICITAR
      ? handleSolicitar
      : modo === MODO_REDEFINIR
        ? handleRedefinir
        : handleLogin

  return (
    <div className="login-screen fo-auth">
      <div className="fo-auth-stripes" aria-hidden="true" />
      <aside className="login-side" aria-label="Identidade FleetOps">
        <div className="login-side-content">
          <BrandLogo variant="vertical" className="login-brand-logo" />
          <p className="login-tagline">Sua frota, sempre no controle.</p>
          <p className="login-side-copy">
            Solicite, aprove e acompanhe o uso dos veículos em um só lugar — com mais eficiência e
            menos custos.
          </p>
        </div>
      </aside>

      <div className="login-form-wrap">
        <form className="login-form fo-card-auth" onSubmit={onSubmit} noValidate>
          <BrandLogo variant="horizontal" className="login-form-logo" />
          <div className="login-form-heading">
            <h2>{titulo}</h2>
            <p className="login-subtitle">{subtitulo}</p>
          </div>

          <label className="field">
            <span>Matrícula</span>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              autoFocus
              value={matricula}
              onChange={(e) => setMatricula(filtrarDigitosMatricula(e.target.value))}
              placeholder="Ex.: 012345"
              required
              disabled={loading}
              autoComplete="username"
              maxLength={50}
            />
          </label>

          {modo === MODO_LOGIN && !primeiroAcesso && (
            <PasswordField
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              autoComplete="current-password"
            />
          )}

          {modo === MODO_REDEFINIR && (
            <>
              <label className="field">
                <span>Código de recuperação</span>
                <input
                  type="text"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value.toUpperCase())}
                  placeholder="Código fornecido pelo administrador"
                  required
                  disabled={loading}
                  autoComplete="one-time-code"
                  spellCheck={false}
                />
              </label>
              <PasswordField
                label="Nova senha"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                minLength={8}
                autoComplete="new-password"
                error={textoCampo(fieldErrors, 'password')}
              />
              <PasswordField
                label="Confirmar senha"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
                disabled={loading}
                minLength={8}
                autoComplete="new-password"
                error={textoCampo(fieldErrors, 'password_confirm')}
              />
              <p className="muted-note login-password-hint">
                Mínimo 8 caracteres; evite senhas comuns, só números ou dados pessoais.
              </p>
            </>
          )}

          {sucesso && <div className="form-success" role="status">{sucesso}</div>}
          {error && <div className="form-error" role="alert">{error}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading
              ? 'Aguarde…'
              : modo === MODO_SOLICITAR
                ? 'Solicitar código'
                : modo === MODO_REDEFINIR
                  ? 'Redefinir senha'
                  : primeiroAcesso
                    ? 'Continuar'
                    : 'Entrar'}
            {!loading && modo === MODO_LOGIN && <ArrowRight size={16} strokeWidth={2} aria-hidden />}
          </button>

          <div className="login-aux-links">
            {modo === MODO_LOGIN && (
              <>
                <button
                  type="button"
                  className="btn btn-ghost btn-block"
                  disabled={loading}
                  onClick={() => {
                    limparFeedback()
                    setPassword('')
                    setPrimeiroAcesso((v) => !v)
                  }}
                >
                  {primeiroAcesso ? 'Já tenho senha' : 'Primeiro acesso (sem senha)'}
                </button>
                {!primeiroAcesso && (
                  <>
                    <button
                      type="button"
                      className="link login-link"
                      disabled={loading}
                      onClick={() => irPara(MODO_SOLICITAR)}
                    >
                      Esqueci minha senha
                    </button>
                    <button
                      type="button"
                      className="link login-link"
                      disabled={loading}
                      onClick={() => irPara(MODO_REDEFINIR)}
                    >
                      Já tenho um código
                    </button>
                  </>
                )}
              </>
            )}

            {modo === MODO_SOLICITAR && (
              <>
                <button
                  type="button"
                  className="link login-link"
                  disabled={loading}
                  onClick={() => irPara(MODO_REDEFINIR)}
                >
                  Já tenho um código
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-block"
                  disabled={loading}
                  onClick={() => irPara(MODO_LOGIN)}
                >
                  Voltar ao login
                </button>
              </>
            )}

            {modo === MODO_REDEFINIR && (
              <>
                <button
                  type="button"
                  className="link login-link"
                  disabled={loading}
                  onClick={() => irPara(MODO_SOLICITAR)}
                >
                  Solicitar novo código
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-block"
                  disabled={loading}
                  onClick={() => irPara(MODO_LOGIN)}
                >
                  Voltar ao login
                </button>
              </>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
