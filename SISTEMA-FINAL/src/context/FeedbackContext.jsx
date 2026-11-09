import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, Info, OctagonAlert, X } from 'lucide-react'
import ConfirmDialog from '../components/ConfirmDialog'

const FeedbackContext = createContext(null)

const MAX_TOASTS = 5

/**
 * Hierarquia visual FleetOps:
 * - critical: atenção imediata / falha operacional (permanece até fechar ou ~20s)
 * - attention: pendência que exige ação (~14s)
 * - info: confirmação / orientação (~5s)
 * - success: operação concluída (~4.5s) — subnível informativo positivo
 */
const DURACAO_PADRAO = {
  critical: 20000,
  attention: 14000,
  warning: 14000,
  error: 20000,
  info: 5500,
  success: 4500,
}

const META = {
  critical: {
    Icon: OctagonAlert,
    tituloPadrao: 'Atenção crítica',
    role: 'alert',
  },
  attention: {
    Icon: AlertTriangle,
    tituloPadrao: 'Atenção',
    role: 'status',
  },
  warning: {
    Icon: AlertTriangle,
    tituloPadrao: 'Atenção',
    role: 'status',
  },
  error: {
    Icon: OctagonAlert,
    tituloPadrao: 'Erro',
    role: 'alert',
  },
  info: {
    Icon: Info,
    tituloPadrao: 'Informação',
    role: 'status',
  },
  success: {
    Icon: CheckCircle2,
    tituloPadrao: 'Concluído',
    role: 'status',
  },
}

function normalizarTipo(tipo) {
  if (tipo === 'warning') return 'attention'
  if (tipo === 'error') return 'critical'
  return tipo
}

export function FeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [dialogo, setDialogo] = useState(null)
  const proximoId = useRef(0)
  const timers = useRef(new Map())

  const fecharToast = useCallback((id) => {
    const t = timers.current.get(id)
    if (t) {
      clearTimeout(t)
      timers.current.delete(id)
    }
    setToasts((lista) => lista.filter((item) => item.id !== id))
  }, [])

  const notificar = useCallback((tipoBruto, mensagem, opcoes = {}) => {
    const tipo = normalizarTipo(tipoBruto)
    const id = ++proximoId.current
    const chave = opcoes.chave
    const meta = META[tipo] || META.info
    setToasts((lista) => {
      if (chave && lista.some((t) => t.chave === chave)) return lista
      return [
        ...lista,
        {
          id,
          tipo,
          mensagem,
          titulo: opcoes.titulo || meta.tituloPadrao,
          chave,
          acao: opcoes.acao || null,
        },
      ].slice(-MAX_TOASTS)
    })

    const duracao =
      opcoes.duracao === 0 || opcoes.persistente
        ? 0
        : (opcoes.duracao ?? DURACAO_PADRAO[tipo] ?? DURACAO_PADRAO.info)
    if (duracao > 0) {
      const handle = setTimeout(() => fecharToast(id), duracao)
      timers.current.set(id, handle)
    }
  }, [fecharToast])

  const confirmar = useCallback((opcoes) => new Promise((resolve) => {
    setDialogo({ ...opcoes, resolve })
  }), [])

  function responder(confirmado, texto) {
    if (dialogo?.justificativa) dialogo.resolve(confirmado ? texto : null)
    else dialogo?.resolve(confirmado)
    setDialogo(null)
  }

  const valor = useMemo(() => ({
    sucesso: (mensagem, opcoes) => notificar('success', mensagem, opcoes),
    erro: (mensagem, opcoes) => notificar('critical', mensagem, {
      titulo: opcoes?.titulo || 'Não foi possível concluir',
      ...opcoes,
    }),
    critico: (mensagem, opcoes) => notificar('critical', mensagem, opcoes),
    aviso: (mensagem, opcoes) => notificar('attention', mensagem, opcoes),
    atencao: (mensagem, opcoes) => notificar('attention', mensagem, opcoes),
    info: (mensagem, opcoes) => notificar('info', mensagem, opcoes),
    confirmar,
  }), [notificar, confirmar])

  return (
    <FeedbackContext.Provider value={valor}>
      {children}

      {dialogo && (
        <ConfirmDialog
          title={dialogo.titulo}
          message={dialogo.mensagem}
          note={dialogo.nota}
          confirmLabel={dialogo.confirmar}
          cancelLabel={dialogo.cancelar}
          tone={dialogo.tom}
          requireReason={Boolean(dialogo.justificativa)}
          reasonLabel={dialogo.justificativa?.rotulo}
          reasonPlaceholder={dialogo.justificativa?.placeholder}
          initialReason={dialogo.justificativa?.inicial || ''}
          onConfirm={(texto) => responder(true, texto)}
          onCancel={() => responder(false)}
        />
      )}

      <div className="toast-region" aria-live="polite" aria-relevant="additions">
        {toasts.map((t) => {
          const meta = META[t.tipo] || META.info
          const Icon = meta.Icon
          return (
            <div
              key={t.id}
              className={`toast toast-${t.tipo}`}
              role={meta.role}
              data-nivel={t.tipo}
            >
              <span className="toast-icon" aria-hidden="true">
                <Icon size={18} strokeWidth={2.25} />
              </span>
              <div className="toast-content">
                {t.titulo && <strong className="toast-title">{t.titulo}</strong>}
                <p>{t.mensagem}</p>
                {t.acao?.para && (
                  <Link
                    to={t.acao.para}
                    className="toast-action"
                    onClick={() => fecharToast(t.id)}
                  >
                    {t.acao.rotulo || 'Abrir'}
                  </Link>
                )}
              </div>
              <button
                type="button"
                className="toast-close"
                onClick={() => fecharToast(t.id)}
                aria-label="Fechar notificação"
              >
                <X size={16} strokeWidth={2} aria-hidden />
              </button>
            </div>
          )
        })}
      </div>
    </FeedbackContext.Provider>
  )
}

export function useFeedback() {
  const ctx = useContext(FeedbackContext)
  if (!ctx) throw new Error('useFeedback deve ser usado dentro de FeedbackProvider')
  return ctx
}
