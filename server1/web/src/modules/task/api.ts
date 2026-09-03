import type { TaskItem } from '@/types'
import { request } from '@/shared/http'

export async function fetchTasks(projectId?: string): Promise<TaskItem[]> {
  const q = projectId ? `?projectId=${encodeURIComponent(projectId)}` : ''
  return request(`/tasks${q}`)
}

export async function createTask(input: { fileId: string; type: string }): Promise<TaskItem> {
  return request('/tasks', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
