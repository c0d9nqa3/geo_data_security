export type Role = 'admin' | 'operator' | 'auditor' | 'viewer'

export interface UserInfo {
  id: string
  username: string
  displayName: string
  role: Role
  permissions?: string[]
}

export type ProjectStatus = 'active' | 'archived' | 'draft'

export interface Project {
  id: string
  name: string
  code: string
  status: ProjectStatus
  owner: string
  memberCount: number
  fileCount: number
  updatedAt: string
  description: string
}

export type FileKind = 'GeoTIFF' | 'SHP/GeoJSON' | 'DLG' | 'OSGB' | '其他'

export type FileStatus = 'uploaded' | 'checking' | 'transferred' | 'failed'

export interface DataFile {
  id: string
  projectId: string
  projectName: string
  name: string
  kind: FileKind
  sizeMb: number
  status: FileStatus
  hash: string
  uploadedBy: string
  uploadedAt: string
}

export type TaskStatus =
  | 'queued'
  | 'running'
  | 'waiting_review'
  | 'approved'
  | 'rejected'
  | 'failed'

export interface TaskItem {
  id: string
  projectId: string
  projectName: string
  fileId: string
  fileName: string
  type: string
  status: TaskStatus
  progress: number
  createdBy: string
  createdAt: string
  updatedAt: string
}

export type AuditAction =
  | 'login'
  | 'upload'
  | 'create_project'
  | 'submit_task'
  | 'approve'
  | 'reject'
  | 'apply_circulation'
  | 'distribute'
  | 'delete_circulation'
  | 'download_result'
  | 'query_trace'

export interface AuditEvent {
  id: string
  time: string
  actor: string
  action: AuditAction
  projectId?: string
  detail: string
  result: 'success' | 'denied' | 'error'
}

export type CirculationStatus = 'pending' | 'approved' | 'rejected'
export type AuthorizeScope = 'self' | 'project_members'
export type DistributeStatus = 'none' | 'dispatched'

export type CirculationApplyType = 'project' | 'file' | 'task'

export interface CirculationPage {
  items: CirculationItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface CirculationItem {
  id: string
  applyType?: CirculationApplyType | string
  projectId: string
  projectName: string
  taskId?: string
  fileId?: string
  fileName?: string
  resultId?: string
  applyUserId: string
  applyUser: string
  reviewUser: string
  status: CirculationStatus
  purpose: string
  comment: string
  authorizeScope: AuthorizeScope | string
  expireAt: string
  distributeStatus: DistributeStatus | string
  resultHash: string
  createdAt: string
}
