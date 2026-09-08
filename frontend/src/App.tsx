import { Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Loading } from './components/ui'
import { useSession } from './auth/SessionProvider'
import { ApiDocs } from './pages/ApiDocs'
import { CanvasConfig } from './pages/CanvasConfig'
import { KalturaConfig } from './pages/KalturaConfig'
import { KalturaTokens } from './pages/KalturaTokens'
import { Login } from './pages/Login'
import { Logs } from './pages/Logs'
import { Profile } from './pages/Profile'
import { Settings } from './pages/Settings'
import { ZoomConfig } from './pages/ZoomConfig'

export function App() {
  const { session, loading } = useSession()

  if (loading) return <Loading label="Starting" />

  if (!session?.authenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Logs />} />
        <Route path="/kaltura/tokens" element={<KalturaTokens />} />
        <Route path="/kaltura/config" element={<KalturaConfig />} />
        <Route path="/canvas" element={<CanvasConfig />} />
        <Route path="/zoom" element={<ZoomConfig />} />
        <Route path="/api-docs" element={<ApiDocs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/profile" element={<Profile />} />
        {/* Signing in from /login lands here, as does any unknown path. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
