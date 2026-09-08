import { useCallback, useState } from 'react'

import { api } from '../api/client'
import { PageHead } from '../components/PageHead'
import { Alert, Badge, Card, CopyField, Empty, Field, Loading, useToast } from '../components/ui'
import { useResource } from '../components/useResource'
import type { KalturaToken } from '../api/types'

function formatEpoch(value: number | null) {
  if (!value) return '—'
  return new Date(value * 1000).toLocaleString()
}

function expiryBadge(expiry: number | null) {
  if (!expiry) return <Badge>No expiry</Badge>
  const expired = expiry * 1000 < Date.now()
  return expired ? <Badge kind="warn">Expired</Badge> : <Badge kind="ok">Active</Badge>
}

function TokenCard({ token, onChanged }: { token: KalturaToken; onChanged: () => void }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  const remove = async () => {
    if (!confirm(`Delete token ${token.kalturaTokenId}? This cannot be undone.`)) return
    setBusy(true)
    try {
      await api.kaltura.deleteToken(token.kalturaTokenId)
      toast.ok('Token deleted')
      onChanged()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not delete')
      setBusy(false)
    }
  }

  const addNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!note.trim()) return
    setBusy(true)
    try {
      await api.kaltura.addNote(token.kalturaTokenId, note)
      setNote('')
      onChanged()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not add note')
    } finally {
      setBusy(false)
    }
  }

  const removeNote = async (noteId: number) => {
    try {
      await api.kaltura.deleteNote(noteId)
      onChanged()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not delete note')
    }
  }

  return (
    <Card
      title={
        <span className="inline">
          {token.label ? <span>{token.label}</span> : <span className="muted">Unlabelled</span>}
          {expiryBadge(token.expiry)}
        </span>
      }
      description={token.description ?? undefined}
      actions={
        <>
          <button className="btn btn-sm btn-ghost" onClick={() => setOpen((o) => !o)}>
            {open ? 'Less' : 'Details'}
          </button>
          <button className="btn btn-sm btn-danger" onClick={remove} disabled={busy}>
            Delete
          </button>
        </>
      }
    >
      <Field label="App token" wide>
        <CopyField value={token.token} hidden />
      </Field>

      {open && (
        <dl className="kv" style={{ marginTop: 16 }}>
          <dt>Token ID</dt>
          <dd className="mono">{token.kalturaTokenId}</dd>
          <dt>Partner ID</dt>
          <dd>{token.partnerId ?? '—'}</dd>
          <dt>Privileges</dt>
          <dd className="mono">{token.sessionPrivileges || '—'}</dd>
          <dt>Session user</dt>
          <dd>{token.sessionUserId || '—'}</dd>
          <dt>Session duration</dt>
          <dd>{token.sessionDuration ? `${Math.round(token.sessionDuration / 3600)} hours` : '—'}</dd>
          <dt>Expires</dt>
          <dd>{formatEpoch(token.expiry)}</dd>
          <dt>Created</dt>
          <dd>{formatEpoch(token.createdAt)}</dd>
        </dl>
      )}

      <div style={{ marginTop: 18 }}>
        <h3 style={{ marginBottom: 8 }}>Notes</h3>
        {token.notes.length === 0 && <p className="muted" style={{ margin: '0 0 10px' }}>No notes yet.</p>}
        {token.notes.map((n) => (
          <div className="note" key={n.id}>
            <span>{n.content}</span>
            <span className="inline">
              <span className="note-time">
                {n.timestamp ? new Date(n.timestamp).toLocaleDateString() : ''}
              </span>
              <button className="btn btn-sm btn-ghost" onClick={() => void removeNote(n.id)}>
                Remove
              </button>
            </span>
          </div>
        ))}

        <form className="inline" style={{ marginTop: 10 }} onSubmit={addNote}>
          <input
            className="input"
            style={{ flex: 1, minWidth: 180 }}
            placeholder="Add a note…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button className="btn btn-ghost btn-sm" type="submit" disabled={busy || !note.trim()}>
            Add
          </button>
        </form>
      </div>
    </Card>
  )
}

export function KalturaTokens() {
  const toast = useToast()
  const load = useCallback(() => api.kaltura.listTokens(), [])
  const { data, error, loading, refresh } = useResource(load)

  const [form, setForm] = useState({ kalturaTokenId: '', token: '', label: '' })
  const [adding, setAdding] = useState(false)
  const [showAdd, setShowAdd] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setAdding(true)
    try {
      await api.kaltura.addToken({
        kalturaTokenId: form.kalturaTokenId.trim(),
        token: form.token.trim(),
        label: form.label.trim() || undefined,
      })
      toast.ok('Token registered')
      setForm({ kalturaTokenId: '', token: '', label: '' })
      setShowAdd(false)
      await refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not add token')
    } finally {
      setAdding(false)
    }
  }

  const tokens = data?.tokens ?? []

  return (
    <>
      <PageHead title="Kaltura app tokens">
        Tokens registered with this bridge. Vendors reference a token by its label rather than
        holding the token itself.
      </PageHead>

      {error && <Alert kind="error">{error}</Alert>}

      <Card
        title="Register an existing token"
        description="Create the app token in the KMC first, then record its ID and secret here."
        actions={
          <button className="btn btn-sm btn-ghost" onClick={() => setShowAdd((s) => !s)}>
            {showAdd ? 'Cancel' : 'Add token'}
          </button>
        }
        footer={
          showAdd ? (
            <button className="btn btn-primary" form="add-token" type="submit" disabled={adding}>
              Register token
            </button>
          ) : undefined
        }
      >
        {showAdd && (
          <form id="add-token" onSubmit={submit}>
            <div className="row">
              <Field label="App token ID" hint="The Kaltura token ID, e.g. 1_06ukdpod.">
                <input
                  className="input mono"
                  required
                  value={form.kalturaTokenId}
                  onChange={(e) => setForm({ ...form, kalturaTokenId: e.target.value })}
                />
              </Field>
              <Field label="App token" hint="The token secret from the KMC.">
                <input
                  className="input mono"
                  required
                  value={form.token}
                  onChange={(e) => setForm({ ...form, token: e.target.value })}
                />
              </Field>
            </div>
            <Field
              label="Label"
              hint="Optional. Vendors pass this instead of the token when label enforcement is on."
            >
              <input
                className="input"
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </Field>
          </form>
        )}
        {!showAdd && (
          <p className="muted" style={{ margin: 0 }}>
            {tokens.length} token{tokens.length === 1 ? '' : 's'} registered.
          </p>
        )}
      </Card>

      {loading ? (
        <Loading label="Loading tokens" />
      ) : tokens.length === 0 ? (
        <Card>
          <Empty title="No tokens yet">Register your first Kaltura app token above.</Empty>
        </Card>
      ) : (
        <div className="token-list">
          {tokens.map((t) => (
            <TokenCard key={t.kalturaTokenId} token={t} onChanged={() => void refresh()} />
          ))}
        </div>
      )}
    </>
  )
}
