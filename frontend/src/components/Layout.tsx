import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { useSession } from '../auth/SessionProvider'

const THEME_KEY = 'vpib-theme'
type Theme = 'system' | 'light' | 'dark'

function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (localStorage.getItem(THEME_KEY) as Theme) ?? 'system'
    } catch {
      // Private browsing and blocked site data both throw on access.
      return 'system'
    }
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* nothing to persist to; the in-memory choice still applies */
    }
  }, [theme])

  return { theme, setTheme }
}

export function Layout() {
  const { session, logout } = useSession()
  const navigate = useNavigate()
  const { theme, setTheme } = useTheme()

  const features = session?.features ?? { kaltura: false, canvas: false, zoom: false }
  const title = session?.title ?? 'Integration Bridge'
  const initials = title.trim().charAt(0).toUpperCase() || 'I'

  const onLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const cycleTheme = () => {
    setTheme(theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system')
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
            onClick={cycleTheme}
            title={`Theme: ${theme}`}
          >
            {theme === 'system' ? 'Auto' : theme === 'light' ? 'Light' : 'Dark'}
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
