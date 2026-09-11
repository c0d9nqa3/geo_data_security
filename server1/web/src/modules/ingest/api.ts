import type { DataFile, PageResult } from '@/types'
import { request } from '@/shared/http'

export async function fetchFiles(query?: {
  projectId?: string
  page?: number
  pageSize?: number
}): Promise<PageResult<DataFile>> {
  const params = new URLSearchParams()
  if (query?.projectId) params.set('projectId', query.projectId)
  if (query?.page) params.set('page', String(query.page))
  if (query?.pageSize) params.set('pageSize', String(query.pageSize))
  const q = params.toString()
  return request(`/files${q ? `?${q}` : ''}`)
}

export async function uploadFile(input: {
  projectId: string
  kind: string
  name?: string
  file: File
}): Promise<DataFile> {
  const body = new FormData()
  body.append('projectId', input.projectId)
  body.append('kind', input.kind)
  if (input.name?.trim()) {
    body.append('name', input.name.trim())
  }
  body.append('file', input.file, input.file.name)
  return request('/files/upload', {
    method: 'POST',
    body,
  })
}
