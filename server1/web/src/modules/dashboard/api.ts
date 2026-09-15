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

export interface DataVolumePoint {
  period: string
  count: number
  bytes: number
}

export interface DataKindVolume {
  code: string
  label: string
  title: string
  color: string
  totalCount: number
  totalBytes: number
  periodCount: number
  periodBytes: number
  countAlert: boolean
  bytesAlert: boolean
  points: DataVolumePoint[]
}

export interface DataVolumeOverview {
  granularity: 'month' | 'year'
  year: number
  years: number[]
  countThreshold: number
  bytesThreshold: number
  totalCount: number
  totalBytes: number
  unclassifiedCount: number
  unclassifiedBytes: number
  countAlert: boolean
  bytesAlert: boolean
  kinds: DataKindVolume[]
}

export function fetchDashboardOverview(): Promise<DashboardOverview> {
  return request('/dashboard/overview')
}

export function fetchDataVolume(params: {
  granularity: 'month' | 'year'
  year?: number
}): Promise<DataVolumeOverview> {
  const query = new URLSearchParams({ granularity: params.granularity })
  if (params.year) query.set('year', String(params.year))
  return request(`/dashboard/volume?${query.toString()}`)
}
