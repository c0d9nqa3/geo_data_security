import type { DataFile } from '@/types'
import { request } from '@/shared/http'

export async function fetchFiles(projectId?: string): Promise<DataFile[]> {
  const q = projectId ? `?projectId=${encodeURIComponent(projectId)}` : ''
  return request(`/files${q}`)
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
