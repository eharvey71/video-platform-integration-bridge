import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { useSession } from '../auth/SessionProvider'
import { Alert } from '../components/ui'

const OAUTH_ERRORS: Record<string, string> = {
  no_email: 'That account does not expose an email address we can match to a user.',
  unknown_user: 'No user in this bridge matches that account. Contact your administrator.',
  oauth_failed: 'Sign-in with that provider failed. Please try again.',
}

export function Login() {
  const { login } = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const oauthError = params.get('error')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username, password, remember)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="center-page">
      <div className="login-card">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <h1>Integration Bridge</h1>
          <p className="muted" style={{ margin: '5px 0 0' }}>
            Sign in to manage your video platform integrations.
          </p>
        </div>

        <section className="card">
          <div className="card-body">
            {oauthError && <Alert kind="error">{OAUTH_ERRORS[oauthError] ?? 'Sign-in failed.'}</Alert>}
            {error && <Alert kind="error">{error}</Alert>}

            <form onSubmit={submit}>
              <div className="field field-wide">
                <label className="label" htmlFor="username">
                  Username
                </label>
                <input
                  id="username"
                  className="input"
                  autoComplete="username"
                  autoFocus
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className="field field-wide">
                <label className="label" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  className="input"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <label className="check">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                <span className="check-text">Keep me signed in</span>
              </label>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: 6 }}
                disabled={busy}
              >
                {busy && <span className="spinner" aria-hidden="true" />}
                Sign in
              </button>
            </form>
          </div>

          <div className="card-foot" style={{ justifyContent: 'center' }}>
            {/* Full page loads, not fetches: these leave for the provider. */}
            <a className="btn btn-sm btn-ghost" href="/auth/login/github">
              GitHub
            </a>
            <a className="btn btn-sm btn-ghost" href="/auth/login/okta">
              Okta
            </a>
          </div>
        </section>
      </div>
    </div>
  )
}
