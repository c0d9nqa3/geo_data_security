import type { AuditEvent } from '@/types'
import { request } from '@/shared/http'

export async function fetchAudits(action?: string, result?: string): Promise<AuditEvent[]> {
  const q = new URLSearchParams()
  if (action) q.set('action', action)
  if (result) q.set('result', result)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request(`/audit/events${suffix}`)
}
