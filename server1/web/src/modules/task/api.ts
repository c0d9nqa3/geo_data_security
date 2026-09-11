import type { PageResult, TaskItem } from '@/types'
import { request } from '@/shared/http'

export async function fetchTasks(query?: {
  projectId?: string
  applyType?: string
  status?: string
  page?: number
  pageSize?: number
}): Promise<PageResult<TaskItem>> {
  const params = new URLSearchParams()
  if (query?.projectId) params.set('projectId', query.projectId)
  if (query?.applyType) params.set('applyType', query.applyType)
  if (query?.status) params.set('status', query.status)
  if (query?.page) params.set('page', String(query.page))
  if (query?.pageSize) params.set('pageSize', String(query.pageSize))
  const q = params.toString()
  return request(`/tasks${q ? `?${q}` : ''}`)
}

export async function fetchTask(taskId: string): Promise<TaskItem> {
  return request(`/tasks/${encodeURIComponent(taskId)}`)
}

export async function urgeTask(taskId: string): Promise<TaskItem> {
  return request(`/tasks/${encodeURIComponent(taskId)}/urge`, { method: 'POST' })
}

export async function retryTask(taskId: string): Promise<TaskItem> {
  return request(`/tasks/${encodeURIComponent(taskId)}/retry`, { method: 'POST' })
}

export async function withdrawTask(taskId: string): Promise<TaskItem> {
  return request(`/tasks/${encodeURIComponent(taskId)}/withdraw`, { method: 'POST' })
}

export async function deleteTask(taskId: string): Promise<TaskItem> {
  return request(`/tasks/${encodeURIComponent(taskId)}/delete`, { method: 'POST' })
}
