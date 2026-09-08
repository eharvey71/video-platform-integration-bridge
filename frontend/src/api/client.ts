import type {
  CanvasConfig,
  Features,
  KalturaConfig,
  KalturaToken,
  LogsResponse,
  Note,
  SessionState,
  ZoomConfig,
} from './types'

const BASE = '/adminapi'

/** Thrown for any non-2xx response, carrying the server's message. */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

/**
 * The CSRF token is minted server-side into the session and mirrored into a
 * JS-readable cookie; sending it back in a header is the half of the double
 * submit a cross-site page cannot forge. Kept in memory too, because the login
 * response rotates it and the cookie write may not have landed yet.
 */
let csrfToken = ''

export function setCsrfToken(token: string) {
  csrfToken = token
}

function cookieCsrf(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)

  if (init.body !== undefined) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers.set('X-CSRF-Token', csrfToken || cookieCsrf())
  }

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    // same origin, so the session cookie rides along without CORS
    credentials: 'same-origin',
  })

  if (response.status === 204) return undefined as T

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    throw new ApiError(response.status, data?.error ?? `Request failed (${response.status})`)
  }
  return data as T
}

function remember<T extends { csrfToken?: string }>(payload: T): T {
  if (payload?.csrfToken) setCsrfToken(payload.csrfToken)
  return payload
}

export const api = {
  session: {
    get: () => request<SessionState>('/session').then(remember),
    login: (username: string, password: string, remember_: boolean) =>
      request<SessionState>('/session', {
        method: 'POST',
        body: JSON.stringify({ username, password, remember: remember_ }),
      }).then(remember),
    logout: () => request<SessionState>('/session', { method: 'DELETE' }).then(remember),
    apiToken: () => request<{ token: string }>('/session/token', { method: 'POST' }),
  },

  settings: {
    get: () => request<{ title: string; features: Features }>('/settings'),
    setTitle: (title: string) =>
      request<{ title: string }>('/settings/ui', {
        method: 'PUT',
        body: JSON.stringify({ title }),
      }),
    setProxies: (features: Features) =>
      request<{ features: Features }>('/settings/proxies', {
        method: 'PUT',
        body: JSON.stringify(features),
      }),
  },

  users: {
    create: (payload: { username: string; password: string; email: string; role: string }) =>
      request<unknown>('/users', { method: 'POST', body: JSON.stringify(payload) }),
  },

  kaltura: {
    getConfig: () => request<KalturaConfig>('/kaltura/config'),
    saveConfig: (payload: Partial<KalturaConfig>) =>
      request<KalturaConfig>('/kaltura/config', {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
    listTokens: () => request<{ tokens: KalturaToken[] }>('/kaltura/tokens'),
    addToken: (payload: { kalturaTokenId: string; token: string; label?: string }) =>
      request<KalturaToken>('/kaltura/tokens', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    deleteToken: (id: string) =>
      request<void>(`/kaltura/tokens/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    addNote: (id: string, content: string) =>
      request<Note>(`/kaltura/tokens/${encodeURIComponent(id)}/notes`, {
        method: 'POST',
        body: JSON.stringify({ content }),
      }),
    deleteNote: (noteId: number) =>
      request<void>(`/notes/${noteId}`, { method: 'DELETE' }),
  },

  zoom: {
    getConfig: () => request<ZoomConfig>('/zoom/config'),
    saveConfig: (payload: Partial<ZoomConfig> & { clientSecret?: string }) =>
      request<ZoomConfig>('/zoom/config', { method: 'PUT', body: JSON.stringify(payload) }),
    regenerateAccessKey: () =>
      request<{ accessKey: string }>('/zoom/access-key', { method: 'POST' }),
  },

  canvas: {
    getConfig: () => request<CanvasConfig>('/canvas/config'),
    saveConfig: (payload: Partial<CanvasConfig> & { clientSecret?: string }) =>
      request<CanvasConfig>('/canvas/config', { method: 'PUT', body: JSON.stringify(payload) }),
    authorizeUrl: () => request<{ url: string }>('/canvas/authorize-url', { method: 'POST' }),
    revoke: (rowId: number) => request<void>(`/canvas/users/${rowId}`, { method: 'DELETE' }),
  },

  logs: {
    get: (limit = 500) => request<LogsResponse>(`/logs?limit=${limit}`),
  },
}
