import type { AuditEvent, DataFile, Project, TaskItem, UserInfo } from '@/types'

const AUTH_KEY = 'geo_server1_token'
const USER_KEY = 'geo_server1_user'

/** 开发期 mock；后端 gateway 就绪后改为真实 /api 调用 */
const USE_MOCK = true

export function getToken(): string | null {
  return localStorage.getItem(AUTH_KEY)
}

export function getStoredUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    return null
  }
}

function setSession(token: string, user: UserInfo) {
  localStorage.setItem(AUTH_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(AUTH_KEY)
  localStorage.removeItem(USER_KEY)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`/api${path}`, { ...init, headers })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `请求失败: ${res.status}`)
  }
  return res.json() as Promise<T>
}

const mockProjects: Project[] = [
  {
    id: 'prj_1001',
    name: '城区正射影像库',
    code: 'DOM-2026-01',
    status: 'active',
    owner: '张工',
    memberCount: 5,
    fileCount: 12,
    updatedAt: '2026-09-01 16:20',
    description: '城区正射影像采集与水印处理项目',
  },
  {
    id: 'prj_1002',
    name: '河道矢量专题',
    code: 'VEC-2026-03',
    status: 'active',
    owner: '李工',
    memberCount: 3,
    fileCount: 8,
    updatedAt: '2026-08-28 10:05',
    description: '河道边界 SHP/GeoJSON 数据管理',
  },
  {
    id: 'prj_1003',
    name: '园区三维实景',
    code: 'OSGB-2026-02',
    status: 'draft',
    owner: '王工',
    memberCount: 4,
    fileCount: 2,
    updatedAt: '2026-08-20 09:40',
    description: '园区 OSGB 三维模型入库与审核',
  },
]

const mockFiles: DataFile[] = [
  {
    id: 'file_2001',
    projectId: 'prj_1001',
    projectName: '城区正射影像库',
    name: 'tile_A12.tif',
    kind: 'GeoTIFF',
    sizeMb: 1840,
    status: 'transferred',
    hash: 'sha256:8f3a…c91',
    uploadedBy: '张工',
    uploadedAt: '2026-09-01 15:10',
  },
  {
    id: 'file_2002',
    projectId: 'prj_1002',
    projectName: '河道矢量专题',
    name: 'river_boundary.shp',
    kind: 'SHP/GeoJSON',
    sizeMb: 42,
    status: 'checking',
    hash: 'sha256:12ab…77e',
    uploadedBy: '李工',
    uploadedAt: '2026-08-28 09:50',
  },
  {
    id: 'file_2003',
    projectId: 'prj_1003',
    projectName: '园区三维实景',
    name: 'block_03.osgb',
    kind: 'OSGB',
    sizeMb: 6200,
    status: 'uploaded',
    hash: 'sha256:9cd0…aa2',
    uploadedBy: '王工',
    uploadedAt: '2026-08-20 09:12',
  },
]

const mockTasks: TaskItem[] = [
  {
    id: 'task_3001',
    projectId: 'prj_1001',
    projectName: '城区正射影像库',
    fileId: 'file_2001',
    fileName: 'tile_A12.tif',
    type: 'GeoTIFF 水印',
    status: 'waiting_review',
    progress: 100,
    createdBy: '张工',
    createdAt: '2026-09-01 15:30',
    updatedAt: '2026-09-01 16:05',
  },
  {
    id: 'task_3002',
    projectId: 'prj_1002',
    projectName: '河道矢量专题',
    fileId: 'file_2002',
    fileName: 'river_boundary.shp',
    type: '矢量水印',
    status: 'running',
    progress: 62,
    createdBy: '李工',
    createdAt: '2026-08-28 10:00',
    updatedAt: '2026-08-28 10:18',
  },
  {
    id: 'task_3003',
    projectId: 'prj_1003',
    projectName: '园区三维实景',
    fileId: 'file_2003',
    fileName: 'block_03.osgb',
    type: 'OSGB 水印',
    status: 'queued',
    progress: 0,
    createdBy: '王工',
    createdAt: '2026-08-20 09:30',
    updatedAt: '2026-08-20 09:30',
  },
]

const mockAudits: AuditEvent[] = [
  {
    id: 'aud_1',
    time: '2026-09-01 16:06',
    actor: '张工',
    action: 'submit_task',
    projectId: 'prj_1001',
    detail: '提交任务 task_3001（GeoTIFF 水印）',
    result: 'success',
  },
  {
    id: 'aud_2',
    time: '2026-09-01 15:10',
    actor: '张工',
    action: 'upload',
    projectId: 'prj_1001',
    detail: '上传 tile_A12.tif（1.84 GB）',
    result: 'success',
  },
  {
    id: 'aud_3',
    time: '2026-08-28 09:02',
    actor: '李工',
    action: 'login',
    detail: '终端登录成功',
    result: 'success',
  },
  {
    id: 'aud_4',
    time: '2026-08-27 14:22',
    actor: '外部账号',
    action: 'download_result',
    projectId: 'prj_1001',
    detail: '尝试下载未授权结果',
    result: 'denied',
  },
]

export async function login(username: string, password: string): Promise<UserInfo> {
  if (USE_MOCK) {
    await delay(400)
    if (!username || !password) throw new Error('请输入用户名和密码')
    const user: UserInfo = {
      id: 'u_demo',
      username,
      displayName: username === 'admin' ? '系统管理员' : '业务操作员',
      role: username === 'admin' ? 'admin' : 'operator',
    }
    setSession('mock-jwt-token', user)
    return user
  }
  const data = await request<{ token: string; user: UserInfo }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  setSession(data.token, data.user)
  return data.user
}

export async function logout() {
  clearSession()
}

export async function fetchProjects(): Promise<Project[]> {
  if (USE_MOCK) {
    await delay(250)
    return [...mockProjects]
  }
  return request('/projects')
}

export async function fetchFiles(projectId?: string): Promise<DataFile[]> {
  if (USE_MOCK) {
    await delay(250)
    return projectId ? mockFiles.filter((f) => f.projectId === projectId) : [...mockFiles]
  }
  const q = projectId ? `?projectId=${encodeURIComponent(projectId)}` : ''
  return request(`/files${q}`)
}

export async function fetchTasks(projectId?: string): Promise<TaskItem[]> {
  if (USE_MOCK) {
    await delay(250)
    return projectId ? mockTasks.filter((t) => t.projectId === projectId) : [...mockTasks]
  }
  const q = projectId ? `?projectId=${encodeURIComponent(projectId)}` : ''
  return request(`/tasks${q}`)
}

export async function fetchAudits(): Promise<AuditEvent[]> {
  if (USE_MOCK) {
    await delay(250)
    return [...mockAudits]
  }
  return request('/audit/events')
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}
