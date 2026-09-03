import type { Project } from '@/types'
import { request } from '@/shared/http'

export async function fetchProjects(): Promise<Project[]> {
  return request('/projects')
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
