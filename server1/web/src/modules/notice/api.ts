import type { NoticeItem, PageResult } from '@/types'
import { request } from '@/shared/http'

export async function fetchNotices(query?: {
  page?: number
  pageSize?: number
}): Promise<PageResult<NoticeItem>> {
  const params = new URLSearchParams()
  if (query?.page) params.set('page', String(query.page))
  if (query?.pageSize) params.set('pageSize', String(query.pageSize))
  const q = params.toString()
  return request(`/notices${q ? `?${q}` : ''}`)
}

export async function fetchNoticeUnreadCount(): Promise<{ unreadCount: number }> {
  return request('/notices/unread-count')
}

export async function markNoticeRead(id: string): Promise<NoticeItem> {
  return request(`/notices/${encodeURIComponent(id)}/read`, { method: 'POST' })
}

export async function markAllNoticesRead(): Promise<{ unreadCount: number }> {
  return request('/notices/read-all', { method: 'POST' })
}
