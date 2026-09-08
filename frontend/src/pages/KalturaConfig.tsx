import { useCallback, useState } from 'react'

import { api } from '../api/client'
import { PageHead } from '../components/PageHead'
import { Alert, Card, Check, Field, Loading, useToast } from '../components/ui'
import { useResource } from '../components/useResource'

export function KalturaConfig() {
  const toast = useToast()
  const load = useCallback(() => api.kaltura.getConfig(), [])
  const { data, setData, error, loading } = useResource(load)
  const [saving, setSaving] = useState(false)

  if (loading) return <Loading />
  if (error || !data) return <Alert kind="error">{error ?? 'Failed to load configuration'}</Alert>

  const save = async () => {
    setSaving(true)
    try {
      setData(await api.kaltura.saveConfig(data))
      toast.ok('Kaltura configuration saved')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHead title="Kaltura configuration">
        What the proxy will allow through, and the defaults used when it mints a Kaltura session.
      </PageHead>

      <Card
        title="Access restrictions"
        footer={
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            Save
          </button>
        }
      >
        <Field
          label="Allowed category IDs"
          hint="Comma-separated numeric IDs. Anything not listed is rejected. Leave blank to apply no category restriction."
        >
          <input
            className="input mono"
            placeholder="594123,634123"
            value={data.allowedCategories}
            onChange={(e) => setData({ ...data, allowedCategories: e.target.value })}
          />
        </Field>

        <Check
          label="Require label usage"
          hint="Requests must carry a token label as a query parameter, so a vendor never handles the app token itself. Use with care: a label is all a caller needs."
          checked={data.forceLabels}
          onChange={(v) => setData({ ...data, forceLabels: v })}
        />

        {data.allowedCategories.trim() !== '' && (
          <Alert kind="info">
            While a category list is set, lookups by full category name are refused — a name cannot be
            checked against a list of numeric IDs.
          </Alert>
        )}
      </Card>

      <Card
        title="Session defaults"
        description="Applied when the bridge starts a Kaltura session on a caller's behalf."
        footer={
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            Save
          </button>
        }
      >
        <div className="row">
          <Field label="Partner ID">
            <input
              className="input"
              inputMode="numeric"
              value={data.partnerId ?? ''}
              onChange={(e) => setData({ ...data, partnerId: Number(e.target.value) || 0 })}
            />
          </Field>
          <Field label="Session expiry" hint="Seconds.">
            <input
              className="input"
              type="number"
              min={0}
              value={data.sessionExpiry ?? ''}
              onChange={(e) => setData({ ...data, sessionExpiry: Number(e.target.value) || 0 })}
            />
          </Field>
        </div>

        <Check
          label="Cache session tokens locally"
          hint="Stores a generated KS in the database for reuse until it expires. Depends on label enforcement being on."
          checked={data.useLocalStorage}
          onChange={(v) => setData({ ...data, useLocalStorage: v })}
        />
      </Card>
    </>
  )
}
