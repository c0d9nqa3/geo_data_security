export type Role = 'admin' | 'operator' | 'auditor' | 'viewer'

export interface UserInfo {
  id: string
  username: string
  displayName: string
  role: Role
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
