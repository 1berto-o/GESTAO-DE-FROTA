import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import {
  LayoutDashboard,
  Car,
  CalendarDays,
  FileText,
  IdCard,
  ClipboardCheck,
  Users,
  BarChart3,
  Shield,
  KeyRound,
  Building2,
  LogOut,
  Menu,
  X,
  MoreHorizontal,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import AlertasOperacionais from './AlertasOperacionais'
import BrandLogo from './BrandLogo'

const NAV_ITEMS = [
  { to: '/', label: 'Painel', icon: LayoutDashboard, end: true, bottom: true },
  { to: '/veiculos', label: 'Frota', icon: Car, bottom: true },
  { to: '/reservas', label: 'Minhas reservas', adminLabel: 'Reservas', icon: CalendarDays, bottom: true },
  { to: '/minha-cnh', label: 'Minha CNH', icon: IdCard, userOnly: true, bottom: true },
  { to: '/meu-termo', label: 'Meu termo', icon: FileText, userOnly: true },
  { to: '/aprovacoes', label: 'Aprovações', icon: ClipboardCheck, adminOnly: true, bottom: true },
  { to: '/usuarios', label: 'Usuários', icon: Users, adminOnly: true },
  { to: '/setores', label: 'Setores', icon: Building2, adminOnly: true },
  { to: '/recuperacao-senha', label: 'Recuperação', icon: KeyRound, adminOnly: true },
  { to: '/cnh-pendentes', label: 'CNH pendentes', icon: IdCard, adminOnly: true },
  { to: '/termos-pendentes', label: 'Termos pendentes', icon: FileText, adminOnly: true },
  { to: '/relatorios', label: 'Relatórios', icon: BarChart3, adminOnly: true },
  { to: '/auditoria', label: 'Auditoria', icon: Shield, adminOnly: true },
]

const PAGE_META = {
  '/': { title: 'Painel', subtitle: 'Visão geral da sua frota' },
  '/veiculos': { title: 'Frota', subtitle: 'Veículos disponíveis e cadastro' },
  '/reservas': { title: 'Reservas', subtitle: 'Agenda e acompanhamento' },
  '/minha-cnh': { title: 'Minha CNH', subtitle: 'Documento do condutor' },
  '/meu-termo': { title: 'Meu termo', subtitle: 'Termo de responsabilidade' },
  '/aprovacoes': { title: 'Aprovações', subtitle: 'Solicitações pendentes' },
  '/usuarios': { title: 'Usuários', subtitle: 'Contas e permissões' },
  '/setores': { title: 'Setores', subtitle: 'Cadastro organizacional' },
  '/recuperacao-senha': { title: 'Recuperação de senha', subtitle: 'Solicitações e códigos de uso único' },
  '/cnh-pendentes': { title: 'CNH pendentes', subtitle: 'Análise documental' },
  '/termos-pendentes': { title: 'Termos pendentes', subtitle: 'Análise documental' },
  '/relatorios': { title: 'Relatórios', subtitle: 'Indicadores e exportações' },
  '/auditoria': { title: 'Auditoria', subtitle: 'Trilha de eventos' },
}

export default function Layout({ children }) {
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    document.documentElement.classList.add('fo-theme')
    document.documentElement.classList.remove('dark')
    localStorage.removeItem('theme')
  }, [])

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  const items = useMemo(
    () =>
      NAV_ITEMS.filter((item) => {
        if (item.adminOnly && !isAdmin) return false
        if (item.userOnly && isAdmin) return false
        return true
      }),
    [isAdmin]
  )

  const bottomItems = useMemo(() => items.filter((i) => i.bottom).slice(0, 4), [items])

  const pageMeta = useMemo(() => {
    const exact = PAGE_META[location.pathname]
    if (exact) return exact
    const match = Object.entries(PAGE_META).find(([path]) =>
      path !== '/' && location.pathname.startsWith(path)
    )
    return match?.[1] || { title: 'FleetOps', subtitle: 'Sua frota, sempre no controle.' }
  }, [location.pathname])

  function labelOf(item) {
    return isAdmin && item.adminLabel ? item.adminLabel : item.label
  }

  function handleLogout() {
    setMenuOpen(false)
    logout()
    navigate('/login')
  }

  const initials = (user?.nome || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')

  return (
    <div className="app-shell fo-app">
      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <BrandLogo variant="horizontal" className="sidebar-logo" />
        </div>

        <nav className="sidebar-nav" aria-label="Menu principal">
          {items.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                onClick={() => setMenuOpen(false)}
              >
                <Icon className="sidebar-icon-svg" size={18} strokeWidth={1.75} aria-hidden />
                {labelOf(item)}
              </NavLink>
            )
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <span className="avatar">{initials || '?'}</span>
            <div className="user-info">
              <strong>{user?.nome}</strong>
              <small>{isAdmin ? 'Administrador' : `Matrícula ${user?.matricula}`}</small>
            </div>
          </div>
          <button
            className="logout-btn"
            onClick={handleLogout}
            type="button"
            aria-label="Sair da conta"
          >
            <LogOut size={16} strokeWidth={1.75} aria-hidden />
            Sair
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button
            className="icon-btn mobile-menu-btn"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
            type="button"
          >
            {menuOpen ? <X size={20} strokeWidth={1.75} /> : <Menu size={20} strokeWidth={1.75} />}
          </button>
          <div className="topbar-heading">
            <div className="topbar-title">{pageMeta.title}</div>
            <div className="topbar-subtitle">{pageMeta.subtitle}</div>
          </div>
          <div className="topbar-spacer" />
          <div className="topbar-user-pill" title={user?.nome || ''}>
            <span className="avatar avatar-sm">{initials || '?'}</span>
          </div>
        </header>

        <main className="app-content">
          <AlertasOperacionais />
          {children}
        </main>

        <div className="powered-by">
          <span>Desenvolvido por </span>
          <strong>Humberto Oliveira - humbertobezerradeoliveira@gmail.com</strong>
        </div>
      </div>

      <nav className="bottom-nav" aria-label="Atalhos móveis">
        {bottomItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `bottom-nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon className="bottom-nav-icon-svg" size={18} strokeWidth={1.75} aria-hidden />
              <span className="bottom-nav-label">{labelOf(item)}</span>
            </NavLink>
          )
        })}
        <button
          type="button"
          className="bottom-nav-link"
          onClick={() => setMenuOpen(true)}
          aria-label="Mais opções"
        >
          <MoreHorizontal size={18} strokeWidth={1.75} aria-hidden />
          <span className="bottom-nav-label">Mais</span>
        </button>
      </nav>

      {menuOpen && (
        <div className="sidebar-scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" />
      )}
    </div>
  )
}
