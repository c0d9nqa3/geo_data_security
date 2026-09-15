export type Role = 'admin' | 'operator' | 'auditor' | 'viewer'

export interface UserInfo {
  id: string
  username: string
  displayName: string
  role: Role
  permissions?: string[]
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
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

export type FileKind =
  | 'DLG'
  | 'DOM'
  | 'DEM'
  | 'DRG'
  | '基础地理实体数据'
  | '倾斜摄影Mesh三维模型'
  | '激光点云数据'
  | '其他'

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
  | 'pending'
  | 'distributing'
  | 'completed'
  | 'rejected'
  | 'failed'
  | 'withdrawn'
  | 'deleted'
  | 'queued'
  | 'running'
  | 'waiting_review'
  | 'approved'

export interface TaskNode {
  key: string
  label: string
  state: string
  actor?: string
  time?: string
  remark?: string
}

export interface TaskItem {
  id: string
  applyType?: string
  title?: string
  projectId: string
  projectName: string
  fileId?: string
  fileName?: string
  applyUserId?: string
  applyUser?: string
  reviewUser?: string
  type: string
  status: TaskStatus | string
  progress: number
  stage?: string
  currentNode?: string
  currentNodeLabel?: string
  circulationStatus?: string
  distributeStatus?: string
  comment?: string
  purpose?: string
  urgeCount?: number
  lastUrgeAt?: string
  canUrge?: boolean
  canRetry?: boolean
  canWithdraw?: boolean
  canDelete?: boolean
  canDistribute?: boolean
  nodes?: TaskNode[]
  resultId?: string
  outputReady?: boolean
  createdBy?: string
  createdAt: string
  updatedAt: string
}

export interface NoticeItem {
  id: string
  type: string
  title: string
  content: string
  circulationId?: string
  projectId?: string
  projectName?: string
  fileId?: string
  applyType?: string
  applyTypeLabel?: string
  senderUserId?: string
  senderName?: string
  read: boolean
  createdAt: string
}

export interface TaskResultIndex {
  taskId: string
  resultId: string
  resultHash: string
  chainProof: string
  message: string
}

export type AuditAction =
  | 'upload'
  | 'create_project'
  | 'submit_task'
  | 'process_complete'
  | 'approve'
  | 'reject'
  | 'apply_circulation'
  | 'distribute'
  | 'delete_circulation'
  | 'download_result'
  | 'query_trace'
  | 'urge'
  | 'resubmit'
  | 'withdraw'

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
