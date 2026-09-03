import type { CirculationItem, CirculationPage } from '@/types'
import { request } from '@/shared/http'

export async function fetchCirculations(query?: {
  status?: string
  page?: number
  pageSize?: number
}): Promise<CirculationPage> {
  const params = new URLSearchParams()
  if (query?.status) params.set('status', query.status)
  if (query?.page) params.set('page', String(query.page))
  if (query?.pageSize) params.set('pageSize', String(query.pageSize))
  const q = params.toString()
  return request(`/circulations${q ? `?${q}` : ''}`)
}

export async function fetchCirculation(id: string): Promise<CirculationItem> {
  return request(`/circulations/${encodeURIComponent(id)}`)
}

export async function approveCirculation(id: string, comment?: string): Promise<CirculationItem> {
  return request(`/circulations/${encodeURIComponent(id)}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment || '' }),
  })
}

export async function rejectCirculation(id: string, comment?: string): Promise<CirculationItem> {
  return request(`/circulations/${encodeURIComponent(id)}/reject`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment || '' }),
  })
}

export async function distributeCirculation(id: string): Promise<CirculationItem> {
  return request(`/circulations/${encodeURIComponent(id)}/distribute`, {
    method: 'POST',
  })
}
