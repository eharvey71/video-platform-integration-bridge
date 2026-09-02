import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

/* --- Primitives --------------------------------------------------------- */

export function Card({
  title,
  description,
  actions,
  footer,
  children,
}: {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  footer?: ReactNode
  children?: ReactNode
}) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
          {actions && <div className="inline">{actions}</div>}
        </header>
      )}
      {children && <div className="card-body">{children}</div>}
      {footer && <div className="card-foot">{footer}</div>}
    </section>
  )
}

export function Field({
  label,
  hint,
  wide,
  children,
}: {
  label: string
  hint?: ReactNode
  wide?: boolean
  children: ReactNode
}) {
  return (
    <div className={wide ? 'field field-wide' : 'field'}>
      <label className="label">{label}</label>
      {children}
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}

export function Check({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string
  hint?: ReactNode
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <label className="check">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        <span className="check-text">{label}</span>
        {hint && <p className="hint">{hint}</p>}
      </span>
    </label>
  )
}

export function Alert({ kind, children }: { kind: 'error' | 'ok' | 'warn' | 'info'; children: ReactNode }) {
  return <div className={`alert alert-${kind}`}>{children}</div>
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="loading">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children}
    </div>
  )
}

export function Badge({ kind = 'off', children }: { kind?: 'ok' | 'warn' | 'off'; children: ReactNode }) {
  return <span className={`badge badge-${kind}`}>{children}</span>
}

/* --- Copy-to-clipboard secret ------------------------------------------- */

export function CopyField({ value, hidden }: { value: string; hidden?: boolean }) {
  const [revealed, setRevealed] = useState(!hidden)
  const [copied, setCopied] = useState(false)
  const toast = useToast()

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      toast.error('Clipboard is unavailable in this browser')
    }
  }

  return (
    <div className="secret">
      <span className="spacer" style={{ overflow: 'hidden' }}>
        {revealed ? value : '•'.repeat(Math.min(value.length, 40))}
      </span>
      {hidden && (
        <button type="button" className="btn btn-sm btn-ghost" onClick={() => setRevealed((r) => !r)}>
          {revealed ? 'Hide' : 'Show'}
        </button>
      )}
      <button type="button" className="btn btn-sm btn-ghost" onClick={copy}>
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}

/* --- Toasts ------------------------------------------------------------- */

interface Toast {
  id: number
  kind: 'ok' | 'error'
  message: string
}

interface ToastApi {
  ok: (message: string) => void
  error: (message: string) => void
}

const ToastContext = createContext<ToastApi>({ ok: () => {}, error: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const push = useCallback((kind: Toast['kind'], message: string) => {
    const id = Date.now() + Math.random()
    setToasts((current) => [...current, { id, kind, message }])
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 4200)
  }, [])

  const value = useMemo<ToastApi>(
    () => ({ ok: (m) => push('ok', m), error: (m) => push('error', m) }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.kind}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
