import type { AuditEvent, TaskItem } from '@/types'
import { request } from '@/shared/http'

export interface DashboardTrendPoint {
  date: string
  count: number
}

export interface DashboardOverview {
  projectCount: number
  fileCount: number
  runningTaskCount: number
  alertCount: number
  recentTasks: TaskItem[]
  recentAudits: AuditEvent[]
  taskTrend: DashboardTrendPoint[]
  auditTrend: DashboardTrendPoint[]
}

export function fetchDashboardOverview(): Promise<DashboardOverview> {
  return request('/dashboard/overview')
}
