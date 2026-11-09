export default function EmptyState({ icon = null, title, description, action }) {
  return (
    <div className="empty-state">
      {icon != null && <div className="empty-icon">{icon}</div>}
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action}
    </div>
  )
}
