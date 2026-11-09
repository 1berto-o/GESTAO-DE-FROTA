const LABELS = {
  disponivel: 'Disponível',
  em_uso: 'Em uso',
  manutencao: 'Em manutenção',
  inativo: 'Inativo',
  pendente: 'Pendente',
  aprovada: 'Aprovada',
  aprovado: 'Aprovado',
  negada: 'Rejeitada',
  rejeitada: 'Rejeitada',
  em_andamento: 'Em andamento',
  concluida: 'Concluída',
  cancelada: 'Cancelada',
  sem_cnh: 'Sem CNH',
  proxima_vencimento: 'Próxima do vencimento',
  vencida: 'Vencida',
}

const TONE = {
  disponivel: 'success',
  aprovado: 'success',
  concluida: 'success',
  em_uso: 'warning',
  manutencao: 'warning',
  pendente: 'warning',
  proxima_vencimento: 'warning',
  em_andamento: 'info',
  aprovada: 'info',
  negada: 'danger',
  rejeitada: 'danger',
  vencida: 'danger',
  inativo: 'inactive',
  cancelada: 'inactive',
  sem_cnh: 'inactive',
}

export default function StatusBadge({ status }) {
  const label = LABELS[status] || status
  const tone = TONE[status] || 'inactive'
  return (
    <span className={`status-badge fo-badge fo-badge--${tone}`}>
      <span className="status-dot" aria-hidden />
      <span className="status-label">{label}</span>
    </span>
  )
}
