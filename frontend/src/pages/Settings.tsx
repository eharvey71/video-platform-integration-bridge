import { useCallback, useState } from 'react'

import { api } from '../api/client'
import { useSession } from '../auth/SessionProvider'
import { PageHead } from '../components/PageHead'
import { Alert, Card, Check, Field, Loading, useToast } from '../components/ui'
import { useResource } from '../components/useResource'
import type { Features } from '../api/types'

export function Settings() {
  const toast = useToast()
  const { refresh: refreshSession } = useSession()

  const load = useCallback(() => api.settings.get(), [])
  const { data, setData, error, loading } = useResource(load)
  const [saving, setSaving] = useState<string | null>(null)

  if (loading) return <Loading />
  if (error || !data) return <Alert kind="error">{error ?? 'Failed to load settings'}</Alert>

  const saveTitle = async () => {
    setSaving('title')
    try {
      await api.settings.setTitle(data.title)
      await refreshSession()
      toast.ok('Title updated')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not save')
    } finally {
      setSaving(null)
    }
  }

  const saveProxies = async (features: Features) => {
    setSaving('proxies')
    try {
      const result = await api.settings.setProxies(features)
      setData({ ...data, features: result.features })
      await refreshSession()
      toast.ok('Proxies updated. Restart the app for API spec changes to take effect.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not save')
    } finally {
      setSaving(null)
    }
  }

  return (
    <>
      <PageHead title="Settings">Naming and which vendor proxies this bridge exposes.</PageHead>

      <Card
        title="Appearance"
        footer={
          <button className="btn btn-primary" onClick={saveTitle} disabled={saving === 'title'}>
            Save
          </button>
        }
      >
        <Field label="Bridge name" hint="Shown in the header and browser title.">
          <input
            className="input"
            value={data.title}
            onChange={(e) => setData({ ...data, title: e.target.value })}
          />
        </Field>
      </Card>

      <Card
        title="Vendor proxies"
        description="Turning a proxy off hides its screens and stops its API spec being mounted at start-up."
        footer={
          <>
            <button
              className="btn btn-primary"
              onClick={() => void saveProxies(data.features)}
              disabled={saving === 'proxies'}
            >
              Save
            </button>
            <span className="muted" style={{ fontSize: 12.5 }}>
              Mounting a newly enabled API spec requires an app restart.
            </span>
          </>
        }
      >
        <Check
          label="Kaltura"
          hint="App token management and the Kaltura abstraction API."
          checked={data.features.kaltura}
          onChange={(v) => setData({ ...data, features: { ...data.features, kaltura: v } })}
        />
        <Check
          label="Canvas"
          hint="Canvas OAuth2 authorization for instructor-scoped requests."
          checked={data.features.canvas}
          onChange={(v) => setData({ ...data, features: { ...data.features, canvas: v } })}
        />
        <Check
          label="Zoom"
          hint="Zoom recordings and transcript endpoints."
          checked={data.features.zoom}
          onChange={(v) => setData({ ...data, features: { ...data.features, zoom: v } })}
        />
      </Card>
    </>
  )
}
