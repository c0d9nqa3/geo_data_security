import { getToken } from '@/shared/http'

type Json = Record<string, unknown>

async function gdsRequest<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!(init?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const timeoutMs = init?.timeoutMs ?? 60_000
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`/api/gds${path}`, { ...init, headers, signal: controller.signal })
    const payload = await res.json().catch(() => null)
    if (!res.ok) {
      throw new Error(payload?.message || `请求失败 ${res.status}`)
    }
    if (payload?.code !== '0') {
      throw new Error(payload?.message || '业务请求失败')
    }
    return payload.data as T
  } finally {
    window.clearTimeout(timer)
  }
}

async function gdsDownload(path: string, filename: string, timeoutMs = 30 * 60_000) {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`/api/gds${path}`, { headers, signal: controller.signal })
    if (!res.ok) {
      const err = await res.json().catch(() => null)
      throw new Error(err?.message || `下载失败 ${res.status}`)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    window.clearTimeout(timer)
  }
}

export async function fetchGdsHealth() {
  return gdsRequest<Json>('/health')
}

export async function fetchGdsCapabilities() {
  return gdsRequest<Json>('/capabilities')
}

export async function fetchGdsTask(taskId: string) {
  return gdsRequest<Json>(`/tasks/${encodeURIComponent(taskId)}`)
}

export async function fetchGdsIngestSession(uploadId: string) {
  return gdsRequest<Json>(`/ingest/sessions/${encodeURIComponent(uploadId)}`)
}

export async function fetchGdsVerification(resultId: string) {
  return gdsRequest<Json>(`/results/${encodeURIComponent(resultId)}/verification`, { timeoutMs: 120_000 })
}

export async function fetchGdsManifest(resultId: string) {
  return gdsRequest<Json>(`/results/${encodeURIComponent(resultId)}/manifest`, { timeoutMs: 120_000 })
}

export async function postGdsApprove(resultId: string) {
  return gdsRequest<Json>(`/results/${encodeURIComponent(resultId)}/approve`, { method: 'POST', body: '{}' })
}

export async function postGdsExport(resultId: string) {
  return gdsRequest<Json>(`/results/${encodeURIComponent(resultId)}/export`, { method: 'POST', body: '{}' })
}

export async function fetchGdsExportJob(exportId: string) {
  return gdsRequest<Json>(`/exports/${encodeURIComponent(exportId)}`)
}

export async function downloadGdsResultExportCompat(resultId: string) {
  await gdsDownload(
    `/results/${encodeURIComponent(resultId)}/export`,
    `${resultId}-export.zip`,
  )
}

export async function downloadGdsResultFile(resultId: string, filename: string) {
  await gdsDownload(
    `/results/${encodeURIComponent(resultId)}/files/${encodeURIComponent(filename)}`,
    filename.split('/').pop() || filename,
  )
}

export async function searchGdsProvenance(query: {
  projectId?: string
  artifactId?: string
  classification?: string
  inputHash?: string
}) {
  const params = new URLSearchParams()
  if (query.projectId) params.set('projectId', query.projectId)
  if (query.artifactId) params.set('artifactId', query.artifactId)
  if (query.classification) params.set('classification', query.classification)
  if (query.inputHash) params.set('inputHash', query.inputHash)
  const q = params.toString()
  return gdsRequest<Json>(`/provenance/search${q ? `?${q}` : ''}`)
}

export async function queryGdsProvenance(resultId: string) {
  return gdsRequest<Json>(`/provenance/query?resultId=${encodeURIComponent(resultId)}`, {
    method: 'POST',
    body: '{}',
    timeoutMs: 120_000,
  })
}

export async function detectGdsWatermark(body: Json) {
  return gdsRequest<Json>('/watermarks/detect', { method: 'POST', body: JSON.stringify(body) })
}

export async function verifyGdsWatermark(body: Json) {
  return gdsRequest<Json>('/watermarks/verify', { method: 'POST', body: JSON.stringify(body) })
}

export async function fetchFileGdsContext(fileId: string) {
  return gdsRequest<Json>(`/files/${encodeURIComponent(fileId)}/context`)
}

export async function fetchFileGdsVerification(fileId: string) {
  return gdsRequest<Json>(`/files/${encodeURIComponent(fileId)}/verification`, { timeoutMs: 120_000 })
}

export async function fetchFileGdsManifest(fileId: string) {
  return gdsRequest<Json>(`/files/${encodeURIComponent(fileId)}/manifest`, { timeoutMs: 120_000 })
}

export async function postFileGdsExport(fileId: string) {
  return gdsRequest<Json>(`/files/${encodeURIComponent(fileId)}/export`, { method: 'POST', body: '{}' })
}

export async function queryFileGdsProvenance(fileId: string) {
  return gdsRequest<Json>(`/files/${encodeURIComponent(fileId)}/provenance/query`, {
    method: 'POST',
    body: '{}',
    timeoutMs: 120_000,
  })
}

export async function fetchGdsInternalAuditRetention() {
  return gdsRequest<Json>('/internal/audit-retention')
}

export async function fetchGdsInternalTraceVerify() {
  return gdsRequest<Json>('/internal/trace/verify')
}

export async function fetchGdsInternalTraceArtifact(artifactId: string) {
  return gdsRequest<Json>(`/internal/trace/artifacts/${encodeURIComponent(artifactId)}`)
}

export async function fetchGdsAdminOverview() {
  return gdsRequest<Json>('/admin/overview')
}

export async function fetchGdsAdminStorage() {
  return gdsRequest<Json>('/admin/storage')
}

export async function fetchGdsAdminDatabase(table: string, limit = 20, offset = 0) {
  const q = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return gdsRequest<Json>(`/admin/database/${encodeURIComponent(table)}?${q}`)
}

export async function fetchGdsAdminTraceChain() {
  return gdsRequest<Json>('/admin/trace/chain')
}

export async function fetchGdsAdminAudit() {
  return gdsRequest<Json>('/admin/audit')
}

export async function fetchGdsAdminBesu() {
  return gdsRequest<Json>('/admin/besu')
}

export async function fetchGdsAdminRelationship() {
  return gdsRequest<Json>('/admin/relationship')
}

export async function downloadGdsExportZip(exportId: string) {
  await gdsDownload(`/exports/${encodeURIComponent(exportId)}/download`, `${exportId}.zip`)
}
