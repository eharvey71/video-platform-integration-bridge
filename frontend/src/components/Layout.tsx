import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { useSession } from '../auth/SessionProvider'

const THEME_KEY = 'vpib-theme'
type Theme = 'light' | 'dark' | 'system'

// Light unless someone has chosen otherwise. "system" is opt-in rather than the
// default, so a first visit is white regardless of the viewer's OS setting.
const DEFAULT_THEME: Theme = 'light'
const THEME_CYCLE: Theme[] = ['light', 'dark', 'system']
const THEME_LABELS: Record<Theme, string> = { light: 'Light', dark: 'Dark', system: 'Auto' }

function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      const stored = localStorage.getItem(THEME_KEY) as Theme | null
      return stored && THEME_CYCLE.includes(stored) ? stored : DEFAULT_THEME
    } catch {
      // Private browsing and blocked site data both throw on access.
      return DEFAULT_THEME
    }
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') {
      root.removeAttribute('data-theme')
      // Hand native widgets and scrollbars back to the OS preference.
      root.style.colorScheme = 'light dark'
    } else {
      root.setAttribute('data-theme', theme)
      root.style.colorScheme = theme
    }
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* nothing to persist to; the in-memory choice still applies */
    }
  }, [theme])

  const cycle = () => setTheme(THEME_CYCLE[(THEME_CYCLE.indexOf(theme) + 1) % THEME_CYCLE.length])

  return { theme, cycle, label: THEME_LABELS[theme] }
}

export function Layout() {
  const { session, logout } = useSession()
  const navigate = useNavigate()
  const { theme, cycle, label } = useTheme()

  const features = session?.features ?? { kaltura: false, canvas: false, zoom: false }
  const title = session?.title ?? 'Integration Bridge'
  const initials = title.trim().charAt(0).toUpperCase() || 'I'

  const onLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            {initials}
          </span>
          <span>{title}</span>
        </NavLink>

        <nav className="nav">
          <NavLink to="/" end className="nav-link">
            Logs
          </NavLink>
          {features.kaltura && (
            <>
              <NavLink to="/kaltura/tokens" className="nav-link">
                Tokens
              </NavLink>
              <NavLink to="/kaltura/config" className="nav-link">
                Kaltura
              </NavLink>
            </>
          )}
          {features.canvas && (
            <NavLink to="/canvas" className="nav-link">
              Canvas
            </NavLink>
          )}
          {features.zoom && (
            <NavLink to="/zoom" className="nav-link">
              Zoom
            </NavLink>
          )}
          {(features.kaltura || features.zoom) && (
            <NavLink to="/api-docs" className="nav-link">
              API Docs
            </NavLink>
          )}
          <NavLink to="/settings" className="nav-link">
            Settings
          </NavLink>
        </nav>

        <div className="topbar-right">
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={cycle}
            title={`Theme: ${theme}. Click to change.`}
          >
            {label}
          </button>
          <NavLink to="/profile" className="nav-link">
            {session?.user?.username ?? 'Account'}
          </NavLink>
          <button type="button" className="btn btn-sm btn-ghost" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
