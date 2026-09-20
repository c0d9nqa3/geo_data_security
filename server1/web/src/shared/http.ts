import type { UserInfo } from '@/types'

const AUTH_KEY = 'geo_server1_token'
const USER_KEY = 'geo_server1_user'
const DEFAULT_TIMEOUT_MS = 20_000

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

function redirectToLogin() {
  if (window.location.pathname.startsWith('/login')) return
  window.location.replace('/login')
}

export async function request<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const headers = new Headers(init?.headers)
  const isUpload = init?.body instanceof FormData
  if (!isUpload) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const timeoutMs = init?.timeoutMs ?? (isUpload ? 0 : DEFAULT_TIMEOUT_MS)
  const { timeoutMs: _ignored, ...fetchInit } = init ?? {}
  const controller = new AbortController()
  const timeoutId =
    timeoutMs > 0 ? window.setTimeout(() => controller.abort(), timeoutMs) : undefined
  if (init?.signal) {
    init.signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  let res: Response
  try {
    res = await fetch(`/api${path}`, { ...fetchInit, headers, signal: controller.signal })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试')
    }
    throw new Error('网络中断，请检查后端是否在运行')
  } finally {
    if (timeoutId !== undefined) window.clearTimeout(timeoutId)
  }

  const payload = (await res.json().catch(() => null)) as ApiEnvelope<T> | null
  if (res.status === 401 && path !== '/auth/login') {
    clearSession()
    redirectToLogin()
    throw new Error(payload?.message || '登录已失效，请重新登录')
  }
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
