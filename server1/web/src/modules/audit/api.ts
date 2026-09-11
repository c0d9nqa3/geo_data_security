import type { AuditEvent, PageResult } from '@/types'
import { request } from '@/shared/http'

export async function fetchAudits(query?: {
  action?: string
  result?: string
  page?: number
  pageSize?: number
}): Promise<PageResult<AuditEvent>> {
  const q = new URLSearchParams()
  if (query?.action) q.set('action', query.action)
  if (query?.result) q.set('result', query.result)
  if (query?.page) q.set('page', String(query.page))
  if (query?.pageSize) q.set('pageSize', String(query.pageSize))
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request(`/audit/events${suffix}`)
}
