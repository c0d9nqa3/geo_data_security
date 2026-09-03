import type { UserInfo } from '@/types'
import { clearSession, getToken, request, setSession } from '@/shared/http'

export { getStoredUser, getToken, clearSession } from '@/shared/http'

export async function login(username: string, password: string): Promise<UserInfo> {
  const data = await request<{ token: string; user: UserInfo }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  setSession(data.token, data.user)
  return data.user
}

export async function logout() {
  const token = getToken()
  if (token) {
    try {
      await request('/auth/logout', { method: 'POST' })
    } catch {
      // 本地清会话即可
    }
  }
  clearSession()
}
