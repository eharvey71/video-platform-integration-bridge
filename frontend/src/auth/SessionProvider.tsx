import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { api, ApiError } from '../api/client'
import type { SessionState } from '../api/types'

interface SessionContextValue {
  session: SessionState | null
  loading: boolean
  login: (username: string, password: string, remember: boolean) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used inside SessionProvider')
  return ctx
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      setSession(await api.session.get())
    } catch {
      // An unreachable backend is indistinguishable from a dead session here;
      // either way the UI should fall back to the login screen.
      setSession(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (username: string, password: string, remember: boolean) => {
    setSession(await api.session.login(username, password, remember))
  }, [])

  const logout = useCallback(async () => {
    try {
      setSession(await api.session.logout())
    } catch (e) {
      // A 401 means the session was already gone -- the desired end state.
      if (!(e instanceof ApiError && e.status === 401)) throw e
      await refresh()
    }
  }, [refresh])

  return (
    <SessionContext.Provider value={{ session, loading, login, logout, refresh }}>
      {children}
    </SessionContext.Provider>
  )
}
