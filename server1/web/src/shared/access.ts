import { getStoredUser } from '@/modules/auth/api'
import type { UserInfo } from '@/types'

export function currentUser(): UserInfo | null {
  return getStoredUser()
}

export function hasPermission(code: string, user = currentUser()): boolean {
  if (!user) return false
  return (user.permissions ?? []).includes(code)
}

export function canReview(user = currentUser()): boolean {
  return user?.role === 'admin' || hasPermission('review', user)
}

export function canAudit(user = currentUser()): boolean {
  return user?.role === 'admin' || hasPermission('audit', user)
}
