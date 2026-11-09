import { useId, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

/**
 * Campo de senha com alternância mostrar/ocultar.
 * type="button" evita submit; estado local não altera o valor do input.
 */
export default function PasswordField({
  label = 'Senha',
  value,
  onChange,
  id,
  name,
  placeholder = '••••••••',
  required = false,
  disabled = false,
  autoComplete = 'current-password',
  autoFocus = false,
  minLength,
  error,
  className = '',
}) {
  const autoId = useId()
  const inputId = id || autoId
  const [visivel, setVisivel] = useState(false)

  return (
    <label className={`field ${className}`.trim()} htmlFor={inputId}>
      {label ? <span>{label}</span> : null}
      <div className="password-field">
        <input
          id={inputId}
          name={name}
          className="password-input"
          type={visivel ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          minLength={minLength}
        />
        <button
          type="button"
          className="icon-btn password-toggle"
          aria-label={visivel ? 'Ocultar senha' : 'Mostrar senha'}
          aria-pressed={visivel}
          aria-controls={inputId}
          tabIndex={0}
          disabled={disabled}
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            setVisivel((v) => !v)
          }}
          onMouseDown={(e) => {
            // Evita roubo de foco / seleção acidental do input
            e.preventDefault()
          }}
        >
          {visivel ? (
            <EyeOff size={18} strokeWidth={1.75} aria-hidden />
          ) : (
            <Eye size={18} strokeWidth={1.75} aria-hidden />
          )}
        </button>
      </div>
      {error ? <small className="field-error">{error}</small> : null}
    </label>
  )
}
