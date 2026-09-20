import type { AuditAction, AuditEvent } from '@/types'

const ERROR_BY_ACTION: Partial<Record<AuditAction | string, string>> = {
  distribute: '向服务器2分发失败',
  upload: '上传未成功',
  approve: '审批未成功',
  reject: '驳回未成功',
  apply_circulation: '流转申请未成功',
  submit_task: '提交任务未成功',
  create_project: '创建项目未成功',
}

function basename(path: string): string {
  const p = path.replace(/\\/g, '/').trim()
  const i = p.lastIndexOf('/')
  return i >= 0 ? p.slice(i + 1) : p
}

function extractFileName(detail: string): string {
  const pathMatch = detail.match(/[A-Za-z]:\\[^\s]+|V:\\[^\s]+/)
  if (pathMatch) {
    const name = basename(pathMatch[0])
    if (name) return name
  }
  const fileMatch = detail.match(/([\w\u4e00-\u9fa5.-]+\.(zip|tif|tiff|gpkg|shp|osgb|las|laz|dom|dem))/i)
  return fileMatch ? fileMatch[1] : ''
}

function stripIds(detail: string): string {
  return detail
    .replace(/\s*cir_[a-f0-9]+/gi, '')
    .replace(/\s*task=[^\s]+/gi, '')
    .replace(/\s*result=[^\s]+/gi, '')
    .replace(/\s*sourceHash=[^\s]+/gi, '')
    .replace(/\s*resultHash=[^\s]+/gi, '')
    .replace(/[A-Za-z]:\\[^\s]+/g, '')
    .replace(/V:\\[^\s]+/g, '')
    .replace(/\{[\s\S]*\}/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function formatSuccess(action: AuditAction | string, detail: string): string {
  const d = detail.trim()
  if (action === 'query_trace') {
    const m = d.match(/查看文件溯源\s*(.+)/)
    const name = m ? basename(m[1].trim()) : ''
    return name ? `查看文件溯源：${name}` : '查看文件溯源'
  }
  if (action === 'upload') {
    const m = d.match(/上传\s*(.+)/)
    const name = m ? m[1].trim() : ''
    return name ? `上传文件：${basename(name)}` : '上传文件'
  }
  if (action === 'distribute') {
    const typeMatch = d.match(/向服务器2提交(.+?)授权/)
    const label = typeMatch ? typeMatch[1].trim() : '数据'
    const fileName = extractFileName(d)
    return fileName ? `向服务器2提交${label}分发：${fileName}` : `向服务器2提交${label}分发`
  }
  if (action === 'approve' || action === 'reject') {
    const verb = action === 'approve' ? '审批通过' : '已驳回'
    const m = d.match(/(?:通过|驳回)(.+)/)
    const rest = m ? stripIds(m[1]) : stripIds(d)
    return rest ? `${verb}：${rest}` : verb
  }
  if (action === 'apply_circulation') {
    const m = d.match(/流转申请\s*(.+)/) || d.match(/申请\s*(.+)/)
    const rest = m ? stripIds(m[1]) : stripIds(d)
    return rest ? `提交流转申请：${rest}` : '提交流转申请'
  }
  if (action === 'create_project') {
    const cleaned = stripIds(d)
    return cleaned.startsWith('创建') ? cleaned : `创建项目：${cleaned || '—'}`
  }
  if (action === 'urge') return '催办审核'
  if (action === 'withdraw') return '撤回申请'
  if (action === 'resubmit') return '重新提交'
  if (action === 'delete_circulation') return '删除流转单'
  if (action === 'download_result') return '下载处理结果'
  if (action === 'process_complete') return '服务器2处理完成'

  const cleaned = stripIds(d)
  if (!cleaned) return '—'
  if (/^[a-z_]+$/i.test(cleaned.replace(/\s/g, ''))) return '—'
  return cleaned.length > 80 ? `${cleaned.slice(0, 80)}…` : cleaned
}

/** 审计列表「详情」列：面向业务人员，隐藏路径、编号与报错堆栈。 */
export function formatAuditDetail(event: AuditEvent): string {
  if (event.result === 'error') {
    return ERROR_BY_ACTION[event.action] ?? '操作未成功'
  }
  if (event.result === 'denied') {
    return '操作被拒绝'
  }
  return formatSuccess(event.action, event.detail || '')
}
