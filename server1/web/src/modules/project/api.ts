import type { PageResult, Project } from '@/types'
import { request } from '@/shared/http'

export async function fetchProjects(query?: {
  keyword?: string
  page?: number
  pageSize?: number
}): Promise<PageResult<Project>> {
  const params = new URLSearchParams()
  if (query?.keyword) params.set('keyword', query.keyword)
  if (query?.page) params.set('page', String(query.page))
  if (query?.pageSize) params.set('pageSize', String(query.pageSize))
  const q = params.toString()
  return request(`/projects${q ? `?${q}` : ''}`)
}

export async function createProject(input: {
  name: string
  code: string
  description?: string
}): Promise<Project> {
  return request('/projects', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
