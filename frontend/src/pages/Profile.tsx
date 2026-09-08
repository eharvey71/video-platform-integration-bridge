import { useState } from 'react'

import { api } from '../api/client'
import { useSession } from '../auth/SessionProvider'
import { PageHead } from '../components/PageHead'
import { Card, CopyField, Field, useToast } from '../components/ui'

export function Profile() {
  const { session } = useSession()
  const toast = useToast()
  const [token, setToken] = useState<string | null>(null)

  const [form, setForm] = useState({ username: '', password: '', email: '', role: 'admin' })
  const [busy, setBusy] = useState(false)

  const mintToken = async () => {
    try {
      setToken((await api.session.apiToken()).token)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not issue a token')
    }
  }

  const addUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      await api.users.create(form)
      toast.ok(`User ${form.username} added`)
      setForm({ username: '', password: '', email: '', role: 'admin' })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not add user')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHead title="Account" />

      <Card title="Signed in as">
        <dl className="kv">
          <dt>Username</dt>
          <dd>{session?.user?.username}</dd>
          <dt>Email</dt>
          <dd>{session?.user?.email}</dd>
          <dt>Role</dt>
          <dd>{session?.user?.role}</dd>
        </dl>
      </Card>

      <Card
        title="API token"
        description="A short-lived bearer token for calling the vendor APIs directly. Expires in 10 minutes."
        footer={
          <button className="btn btn-ghost" onClick={mintToken}>
            Issue token
          </button>
        }
      >
        {token ? (
          <CopyField value={token} hidden />
        ) : (
          <p className="muted" style={{ margin: 0 }}>
            No token issued in this session.
          </p>
        )}
      </Card>

      <Card
        title="Add a user"
        description="New users sign in with a username and password, or through a matching OAuth account with the same email."
        footer={
          <button className="btn btn-primary" form="add-user" type="submit" disabled={busy}>
            Add user
          </button>
        }
      >
        <form id="add-user" onSubmit={addUser}>
          <div className="row">
            <Field label="Username">
              <input
                className="input"
                required
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </Field>
            <Field label="Email">
              <input
                className="input"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </Field>
          </div>
          <div className="row">
            <Field label="Password" hint="At least 12 characters.">
              <input
                className="input"
                type="password"
                required
                minLength={12}
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </Field>
            <Field label="Role">
              <select
                className="select"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="admin">admin</option>
                <option value="developer">developer</option>
                <option value="viewer">viewer</option>
              </select>
            </Field>
          </div>
        </form>
      </Card>
    </>
  )
}
