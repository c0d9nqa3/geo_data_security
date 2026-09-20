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

/** 上传等下拉框：从后台把当前用户可见项目全部拉齐。 */
export async function fetchAllProjects(): Promise<Project[]> {
  const pageSize = 100
  const first = await fetchProjects({ page: 1, pageSize })
  const items = [...first.items]
  const pages = Math.max(1, first.totalPages || 1)
  for (let page = 2; page <= pages; page++) {
    const next = await fetchProjects({ page, pageSize })
    items.push(...next.items)
  }
  return items
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
