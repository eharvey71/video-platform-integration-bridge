export interface Features {
  kaltura: boolean
  canvas: boolean
  zoom: boolean
}

export interface SessionUser {
  username: string
  email: string
  role: string
}

export interface SessionState {
  authenticated: boolean
  csrfToken: string
  title: string
  features: Features
  user?: SessionUser
}

export interface Note {
  id: number
  content: string
  timestamp: string | null
}

export interface KalturaToken {
  kalturaTokenId: string
  token: string
  partnerId: number | null
  createdAt: number | null
  updatedAt: number | null
  status: number | null
  sessionType: number | null
  expiry: number | null
  sessionDuration: number | null
  sessionUserId: string | null
  sessionPrivileges: string | null
  description: string | null
  label: string | null
  notes: Note[]
}

export interface KalturaConfig {
  allowedCategories: string
  forceLabels: boolean
  partnerId: number | null
  sessionExpiry: number | null
  useLocalStorage: boolean
}

export interface ZoomConfig {
  clientId: string
  accountId: string
  clientSecretSet: boolean
  accessKey: string | null
  requireAccessKey: boolean
}

export interface CanvasAuthorizedUser {
  id: number
  userId: number
  fullName: string | null
  tokenExpiry: number | null
  expired: boolean
}

export interface CanvasConfig {
  baseUrl: string
  clientId: number | string
  redirectUri: string
  clientSecretSet: boolean
  authorizedUsers: CanvasAuthorizedUser[]
}

export interface LogsResponse {
  lines: string[]
  total?: number
}
