import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api } from '../api/client'
import { PageHead } from '../components/PageHead'
import { Alert, Badge, Card, Empty, Field, Loading, useToast } from '../components/ui'
import { useResource } from '../components/useResource'

const CALLBACK_MESSAGES: Record<string, { kind: 'error' | 'ok'; text: string }> = {
  invalid_state: {
    kind: 'error',
    text: 'Authorization was rejected: the state value did not match. Start the authorization again from this page.',
  },
  no_code: { kind: 'error', text: 'Canvas did not return an authorization code.' },
  exchange_failed: {
    kind: 'error',
    text: 'Canvas would not exchange the code for a token. Check the client ID, secret and redirect URI.',
  },
  authorized: { kind: 'ok', text: 'Canvas user authorized.' },
  already_authorized: { kind: 'ok', text: 'That Canvas user was already authorized.' },
}

export function CanvasConfig() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const load = useCallback(() => api.canvas.getConfig(), [])
  const { data, setData, error, loading, refresh } = useResource(load)

  const [secret, setSecret] = useState('')
  const [saving, setSaving] = useState(false)
  const [callback, setCallback] = useState<{ kind: 'error' | 'ok'; text: string } | null>(null)

  // The OAuth callback redirects back here with a query flag; surface it once
  // and strip it so a refresh does not repeat the message.
  useEffect(() => {
    const key = params.get('error') ?? params.get('status')
    if (!key) return
    setCallback(CALLBACK_MESSAGES[key] ?? null)
    params.delete('error')
    params.delete('status')
    setParams(params, { replace: true })
  }, [params, setParams])

  if (loading) return <Loading />
  if (error || !data) return <Alert kind="error">{error ?? 'Failed to load configuration'}</Alert>

  const save = async () => {
    setSaving(true)
    try {
      setData(
        await api.canvas.saveConfig({
          baseUrl: data.baseUrl,
          clientId: data.clientId,
          redirectUri: data.redirectUri,
          ...(secret ? { clientSecret: secret } : {}),
        }),
      )
      setSecret('')
      toast.ok('Canvas configuration saved')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const authorize = async () => {
    try {
      // Minted server-side so the CSRF state lands in the session before we leave.
      const { url } = await api.canvas.authorizeUrl()
      window.location.href = url
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not start authorization')
    }
  }

  const revoke = async (rowId: number, name: string | null) => {
    if (!confirm(`Remove the stored Canvas authorization for ${name ?? 'this user'}?`)) return
    try {
      await api.canvas.revoke(rowId)
      toast.ok('Authorization removed')
      await refresh()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not remove')
    }
  }

  return (
    <>
      <PageHead title="Canvas configuration">
        The OAuth2 developer key this bridge uses, and the instructors who have authorized it.
      </PageHead>

      {callback && <Alert kind={callback.kind}>{callback.text}</Alert>}

      <Card
        title="Developer key"
        description="From Canvas: Admin → Developer Keys."
        footer={
          <>
            <button className="btn btn-primary" onClick={save} disabled={saving}>
              Save
            </button>
            <button className="btn btn-ghost" onClick={authorize} disabled={!data.baseUrl || !data.redirectUri}>
              Start authorization
            </button>
          </>
        }
      >
        <Field label="Canvas base URL" hint="e.g. https://school.instructure.com">
          <input
            className="input"
            value={data.baseUrl}
            onChange={(e) => setData({ ...data, baseUrl: e.target.value })}
          />
        </Field>

        <div className="row">
          <Field label="Client ID">
            <input
              className="input mono"
              inputMode="numeric"
              value={data.clientId}
              onChange={(e) => setData({ ...data, clientId: e.target.value })}
            />
          </Field>
          <Field label="Redirect URI" hint="Must match the key exactly.">
            <input
              className="input mono"
              value={data.redirectUri}
              onChange={(e) => setData({ ...data, redirectUri: e.target.value })}
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
        title="Authorized users"
        description="Access and refresh tokens are held server-side and never returned to this page."
      >
        {data.authorizedUsers.length === 0 ? (
          <Empty title="Nobody has authorized yet">
            Use “Start authorization” above to connect the first Canvas account.
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Canvas user ID</th>
                  <th>Token</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.authorizedUsers.map((u) => (
                  <tr key={u.id}>
                    <td>{u.fullName ?? <span className="muted">Unknown</span>}</td>
                    <td className="mono">{u.userId}</td>
                    <td>
                      {u.expired ? <Badge kind="warn">Expired</Badge> : <Badge kind="ok">Valid</Badge>}
                    </td>
                    <td className="nowrap" style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => void revoke(u.id, u.fullName)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
