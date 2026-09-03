import type { UserInfo } from '@/types'

const AUTH_KEY = 'geo_server1_token'
const USER_KEY = 'geo_server1_user'

interface ApiEnvelope<T> {
  code: string
  message: string
  retryable?: boolean
  requestId?: string
  data: T
}

export function getToken(): string | null {
  return localStorage.getItem(AUTH_KEY)
}

export function getStoredUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    return null
  }
}

export function setSession(token: string, user: UserInfo) {
  localStorage.setItem(AUTH_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(AUTH_KEY)
  localStorage.removeItem(USER_KEY)
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!(init?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`/api${path}`, { ...init, headers })
  const payload = (await res.json().catch(() => null)) as ApiEnvelope<T> | null
  if (!res.ok) {
    throw new Error(payload?.message || `请求失败: ${res.status}`)
  }
  if (payload && typeof payload === 'object' && 'code' in payload) {
    if (payload.code !== '0') {
      throw new Error(payload.message || '业务请求失败')
    }
    return payload.data
  }
  return payload as T
}
