import { useCallback, useState } from 'react'

import { api } from '../api/client'
import { PageHead } from '../components/PageHead'
import { Alert, Badge, Card, Check, CopyField, Field, Loading, useToast } from '../components/ui'
import { useResource } from '../components/useResource'

export function ZoomConfig() {
  const toast = useToast()
  const load = useCallback(() => api.zoom.getConfig(), [])
  const { data, setData, error, loading } = useResource(load)

  const [secret, setSecret] = useState('')
  const [saving, setSaving] = useState(false)

  if (loading) return <Loading />
  if (error || !data) return <Alert kind="error">{error ?? 'Failed to load configuration'}</Alert>

  const save = async () => {
    setSaving(true)
    try {
      const result = await api.zoom.saveConfig({
        clientId: data.clientId,
        accountId: data.accountId,
        requireAccessKey: data.requireAccessKey,
        // Omitted when blank, so saving the rest of the form leaves the stored
        // secret alone rather than blanking it.
        ...(secret ? { clientSecret: secret } : {}),
      })
      setData(result)
      setSecret('')
      toast.ok('Zoom configuration saved')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const regenerate = async () => {
    if (!confirm('Regenerate the access key? Any vendor using the current key will start getting 401s.'))
      return
    try {
      const { accessKey } = await api.zoom.regenerateAccessKey()
      setData({ ...data, accessKey })
      toast.ok('Access key regenerated')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not regenerate')
    }
  }

  return (
    <>
      <PageHead title="Zoom configuration">
        Server-to-server OAuth credentials, and the key vendors present to reach the Zoom endpoints.
      </PageHead>

      <Card
        title="Server-to-server OAuth app"
        description="From your Zoom Marketplace app's App Credentials tab."
        footer={
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            Save
          </button>
        }
      >
        <div className="row">
          <Field label="Client ID">
            <input
              className="input mono"
              value={data.clientId}
              onChange={(e) => setData({ ...data, clientId: e.target.value })}
            />
          </Field>
          <Field label="Account ID">
            <input
              className="input mono"
              value={data.accountId}
              onChange={(e) => setData({ ...data, accountId: e.target.value })}
            />
          </Field>
        </div>

        <Field
          label="Client secret"
          hint={
            data.clientSecretSet
              ? 'A secret is stored. It is never sent back to the browser — leave this blank to keep it.'
              : 'No secret stored yet.'
          }
        >
          <input
            className="input mono"
            type="password"
            autoComplete="new-password"
            placeholder={data.clientSecretSet ? '•••••••• (unchanged)' : ''}
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </Field>
      </Card>

      <Card
        title={
          <span className="inline">
            API access key
            {data.requireAccessKey ? <Badge kind="ok">Enforced</Badge> : <Badge kind="warn">Not enforced</Badge>}
          </span>
        }
        description="Callers send this as the X-Access-Key header on the Zoom endpoints."
        actions={
          <button className="btn btn-sm btn-ghost" onClick={regenerate}>
            Regenerate
          </button>
        }
        footer={
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            Save
          </button>
        }
      >
        {data.accessKey ? (
          <Field label="Current key" wide>
            <CopyField value={data.accessKey} hidden />
          </Field>
        ) : (
          <p className="muted">No key generated yet. Save this form to create one.</p>
        )}

        <Check
          label="Require the access key"
          hint="Leave this on. With it off the Zoom API spec still refuses callers, so turning it off does not open the endpoints — it takes them out of service."
          checked={data.requireAccessKey}
          onChange={(v) => setData({ ...data, requireAccessKey: v })}
        />
      </Card>
    </>
  )
}
