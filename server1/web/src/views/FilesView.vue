<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="projectFilter">
        <option value="">全部项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ projectLabel(p) }}</option>
      </select>
      <button type="button" class="primary" @click="openUpload">上传数据</button>
    </div>
    <p class="hint">
      {{ reviewer ? '管理员可查看全部上传文件。' : '你只能看到自己上传的文件，入库后可发起处理作业。' }}
      点「查看溯源」可看该文件从上传、审核、分发到服务器2解析、安全处理、上链和校验的完整节点。
    </p>

    <div class="table-wrap">
      <div v-if="loading" class="empty-inline">加载中…</div>
      <table v-else>
        <thead>
          <tr>
            <th>文件</th>
            <th>类型</th>
            <th>所属项目</th>
            <th>大小</th>
            <th>状态</th>
            <th>文件 ID</th>
            <th>上传人</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.id">
            <td class="name">{{ f.name }}</td>
            <td>{{ f.kind }}</td>
            <td>{{ fileProjectName(f) }}</td>
            <td>{{ f.sizeMb }} MB</td>
            <td><span class="tag" :data-s="f.status">{{ statusText(f.status) }}</span></td>
            <td><code>{{ f.id }}</code></td>
            <td>{{ f.uploadedBy }}</td>
            <td>{{ f.uploadedAt }}</td>
            <td>
              <div class="ops">
                <button type="button" class="btn-mini" @click="openTrace(f)">查看溯源</button>
                <button
                  v-if="f.status === 'transferred'"
                  type="button"
                  class="btn-mini"
                  @click="startProcess(f.id)"
                >
                  发起处理
                </button>
                <span v-else class="muted">入库后可处理</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !files.length" class="empty-inline">暂无文件</div>
      <PagerBar v-model:page="page" v-model:page-size="pageSize" :total="total" :total-pages="totalPages" :loading="loading" />
    </div>

    <div v-if="showUpload" class="modal-mask" @click.self="closeUpload">
      <form class="modal" @submit.prevent="onUpload">
        <h3>上传数据到服务器1</h3>
        <label>
          目标项目
          <select v-model="form.projectId" required>
            <option disabled value="">请选择</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ projectLabel(p) }}</option>
          </select>
        </label>
        <label>
          本地文件
          <input
            ref="fileInput"
            class="file-input"
            type="file"
            required
            @change="onPickFile"
          />
        </label>
        <p v-if="pickedFile" class="tip">
          已选择 {{ pickedFile.name }}（{{ formatSize(pickedFile.size) }}）
        </p>
        <label>
          数据类型
          <select v-model="form.kind">
            <option v-for="k in fileKinds" :key="k.value" :value="k.value">
              {{ k.label ? `${k.title}（${k.label}）` : k.title }}
            </option>
          </select>
        </label>
        <label>
          显示名称（可选）
          <input v-model="form.name" placeholder="默认使用本地文件名" />
        </label>
        <p v-if="errorMsg" class="tip" style="color: var(--danger)">{{ errorMsg }}</p>
        <p class="tip">提交后自动进入流转待办和任务管理流程图。管理员审核通过后，提交人可到流转控制向服务器2分发。未审核前可在任务管理撤回。</p>
        <div class="actions">
          <button type="button" class="ghost" @click="closeUpload">取消</button>
          <button type="submit" class="primary" :disabled="submitting || !pickedFile">
            {{ submitting ? '上传中…' : '确认上传' }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="traceOpen" class="modal-mask" @click.self="closeTrace">
      <div class="modal trace-modal">
        <h3>{{ traceFile?.name || '文件溯源' }}</h3>
        <p class="tip">
          {{ trace?.projectName || traceFile?.projectName }}
          · 当前节点 {{ trace?.currentLabel || (traceLoading ? '查询中…' : '—') }}
        </p>
        <p v-if="trace?.liveHint" class="tip">{{ trace.liveHint }}</p>
        <p v-if="traceError" class="tip" style="color: var(--danger)">{{ traceError }}</p>
        <div v-if="traceLoading" class="empty-inline">正在拉取溯源节点…</div>
        <ol v-else-if="trace" class="trace">
          <li v-for="n in trace.nodes" :key="n.key" :data-s="n.state">
            <span class="dot" :data-s="n.state" />
            <div class="trace-body">
              <div class="trace-head">
                <strong>{{ n.label }}</strong>
                <em>{{ nodeStateText(n.state) }}</em>
              </div>
              <p v-if="n.remark">{{ n.remark }}</p>
              <span v-if="n.actor || n.time" class="muted">{{ [n.actor, n.time].filter(Boolean).join(' · ') }}</span>
            </div>
          </li>
        </ol>
        <dl v-if="trace && !traceLoading" class="meta">
          <div><dt>文件 ID</dt><dd><code>{{ trace.fileId }}</code></dd></div>
          <div v-if="trace.evidence.taskId"><dt>服务器2任务</dt><dd><code>{{ trace.evidence.taskId }}</code></dd></div>
          <div v-if="trace.evidence.resultId"><dt>结果 ID</dt><dd><code>{{ trace.evidence.resultId }}</code></dd></div>
          <div v-if="trace.evidence.sourcePath"><dt>落盘路径</dt><dd class="wrap">{{ trace.evidence.sourcePath }}</dd></div>
          <div v-if="trace.evidence.verified != null"><dt>校验</dt><dd>{{ trace.evidence.verified ? '通过' : '未通过' }}{{ trace.evidence.method ? ` · ${trace.evidence.method}` : '' }}</dd></div>
          <div v-if="trace.evidence.filesProcessed != null"><dt>处理文件</dt><dd>{{ trace.evidence.matched ?? '—' }} / {{ trace.evidence.filesProcessed }}</dd></div>
          <div v-if="trace.evidence.onChain != null"><dt>上链</dt><dd>{{ trace.evidence.onChain ? '已上链' : '未上链' }}</dd></div>
          <div v-if="trace.evidence.chainBlock"><dt>区块</dt><dd>{{ trace.evidence.chainBlock }}</dd></div>
        </dl>
        <p v-if="gdsDetail" class="tip gds-detail">{{ gdsDetail.startsWith('{') ? '接口返回：\n' + gdsDetail : gdsDetail }}</p>
        <GdsVerificationPanel v-if="gdsVerification" :data="gdsVerification" />
        <div v-if="trace?.evidence.resultId" class="trace-gds-actions">
          <button type="button" class="ghost" :disabled="gdsBusy" @click="refreshGdsVerification">
            {{ gdsBusy ? '查询中…' : '校验结果' }}
          </button>
          <button type="button" class="ghost" :disabled="gdsBusy" @click="loadTraceManifest">成果清单</button>
          <button type="button" class="ghost" :disabled="gdsBusy" @click="loadTraceProvQuery">溯源详情</button>
          <button type="button" class="ghost" :disabled="gdsBusy" @click="startTraceExport">创建导出</button>
          <button v-if="trace.evidence.taskId" type="button" class="ghost" :disabled="gdsBusy" @click="loadTraceTask">
            任务状态
          </button>
        </div>
        <div class="actions">
          <button type="button" class="ghost" @click="closeTrace">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchFiles, fetchFileProvenance, uploadFile } from '@/modules/ingest/api'
import {
  fetchFileGdsManifest,
  fetchFileGdsVerification,
  fetchGdsTask,
  postFileGdsExport,
  queryFileGdsProvenance,
} from '@/modules/gds/api'
import GdsVerificationPanel from '@/modules/gds/GdsVerificationPanel.vue'
import { fetchAllProjects } from '@/modules/project/api'
import { canReview } from '@/shared/access'
import PagerBar from '@/shared/PagerBar.vue'
import type { DataFile, FileKind, FileProvenance, Project } from '@/types'

const router = useRouter()
const reviewer = canReview()

const loading = ref(true)
const files = ref<DataFile[]>([])
const projects = ref<Project[]>([])
const total = ref(0)
const totalPages = ref(1)
const page = ref(1)
const pageSize = ref(10)
const projectFilter = ref('')
const showUpload = ref(false)
const submitting = ref(false)
const errorMsg = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const pickedFile = ref<File | null>(null)
const traceOpen = ref(false)
const traceLoading = ref(false)
const traceError = ref('')
const traceFile = ref<DataFile | null>(null)
const trace = ref<FileProvenance | null>(null)
const gdsBusy = ref(false)
const gdsDetail = ref('')
const gdsVerification = ref<Record<string, unknown> | null>(null)
const form = reactive({
  projectId: '',
  kind: 'DLG' as FileKind,
  name: '',
})

const fileKinds: { value: FileKind; label: string; title: string }[] = [
  { value: 'DLG', label: 'DLG', title: '数字线划地图' },
  { value: 'DOM', label: 'DOM', title: '数字正射影像' },
  { value: 'DEM', label: 'DEM', title: '数字高程模型' },
  { value: 'DRG', label: 'DRG', title: '数字栅格地图' },
  { value: '基础地理实体数据', label: '', title: '基础地理实体数据' },
  { value: '倾斜摄影Mesh三维模型', label: '', title: '倾斜摄影Mesh三维模型' },
  { value: '激光点云数据', label: '', title: '激光点云数据' },
]

function statusText(s: DataFile['status']) {
  return (
    {
      uploaded: '已接收',
      checking: '校验中',
      transferred: '已转交服务器2',
      failed: '失败',
    } as const
  )[s]
}

function looksGarbled(name?: string) {
  const value = (name || '').trim()
  if (!value) return true
  return value.includes('?') || value.includes('？')
}

function projectLabel(p: Project) {
  if (!looksGarbled(p.name)) {
    return p.name
  }
  return p.code || p.id
}

function fileProjectName(file: DataFile) {
  if (!looksGarbled(file.projectName)) {
    return file.projectName
  }
  const hit = projects.value.find((p) => p.id === file.projectId)
  return hit ? projectLabel(hit) : file.projectId
}

async function loadProjects() {
  try {
    projects.value = await fetchAllProjects()
  } catch {
    projects.value = []
  }
}

async function openUpload() {
  await loadProjects()
  showUpload.value = true
}

function startProcess(fileId: string) {
  router.push({ name: 'tasks', query: { fileId } })
}

function nodeStateText(s?: string) {
  const map: Record<string, string> = {
    done: '已完成',
    current: '进行中',
    waiting: '未到达',
    skipped: '已跳过',
    rejected: '已驳回',
    failed: '失败',
  }
  return map[s || ''] ?? s ?? ''
}

async function openTrace(file: DataFile) {
  traceFile.value = file
  traceOpen.value = true
  traceLoading.value = true
  traceError.value = ''
  trace.value = null
  gdsDetail.value = ''
  gdsVerification.value = null
  try {
    trace.value = await fetchFileProvenance(file.id)
  } catch (e) {
    traceError.value = e instanceof Error ? e.message : '溯源查询失败'
  } finally {
    traceLoading.value = false
  }
}

function closeTrace() {
  traceOpen.value = false
  traceLoading.value = false
  traceError.value = ''
  traceFile.value = null
  trace.value = null
  gdsDetail.value = ''
  gdsVerification.value = null
  gdsBusy.value = false
}

function traceFileId(): string | undefined {
  return traceFile.value?.id
}

async function runGdsAction(fn: () => Promise<void>) {
  gdsBusy.value = true
  gdsDetail.value = ''
  try {
    await fn()
  } catch (e) {
    gdsDetail.value = e instanceof Error ? e.message : '操作失败'
    gdsVerification.value = null
  } finally {
    gdsBusy.value = false
  }
}

async function refreshGdsVerification() {
  const fid = traceFileId()
  if (!fid || !trace.value?.evidence.resultId) return
  await runGdsAction(async () => {
    const data = await fetchFileGdsVerification(fid)
    gdsVerification.value = data
    gdsDetail.value = ''
  })
}

async function loadTraceManifest() {
  const fid = traceFileId()
  if (!fid) return
  await runGdsAction(async () => {
    gdsVerification.value = null
    gdsDetail.value = JSON.stringify(await fetchFileGdsManifest(fid), null, 2)
  })
}

async function loadTraceProvQuery() {
  const fid = traceFileId()
  if (!fid) return
  await runGdsAction(async () => {
    gdsVerification.value = null
    gdsDetail.value = JSON.stringify(await queryFileGdsProvenance(fid), null, 2)
  })
}

async function startTraceExport() {
  const fid = traceFileId()
  if (!fid) return
  await runGdsAction(async () => {
    gdsVerification.value = null
    gdsDetail.value = JSON.stringify(await postFileGdsExport(fid), null, 2)
  })
}

async function loadTraceTask() {
  const taskId = trace.value?.evidence.taskId
  if (!taskId) return
  await runGdsAction(async () => {
    gdsVerification.value = null
    gdsDetail.value = JSON.stringify(await fetchGdsTask(taskId), null, 2)
  })
}

function inferKind(name: string): FileKind {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'dlg' || ext === 'dxf') return 'DLG'
  if (ext === 'tif' || ext === 'tiff' || ext === 'img' || ext === 'sid' || ext === 'jp2') return 'DOM'
  if (ext === 'dem' || ext === 'asc' || ext === 'bil' || ext === 'hgt') return 'DEM'
  if (ext === 'drg') return 'DRG'
  if (ext === 'shp' || ext === 'geojson' || ext === 'json' || ext === 'gpkg' || ext === 'gdb') return '基础地理实体数据'
  if (ext === 'osgb' || ext === 'obj' || ext === 'gltf' || ext === 'glb' || ext === '3mx') return '倾斜摄影Mesh三维模型'
  if (ext === 'las' || ext === 'laz' || ext === 'xyz' || ext === 'e57' || ext === 'pts') return '激光点云数据'
  return 'DLG'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function onPickFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  pickedFile.value = file
  if (file) {
    form.name = file.name
    form.kind = inferKind(file.name)
  }
}

function closeUpload() {
  showUpload.value = false
  errorMsg.value = ''
  form.name = ''
  form.projectId = ''
  pickedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

onMounted(async () => {
  await loadProjects()
  await reload()
})

watch(projectFilter, () => {
  page.value = 1
})
watch(pageSize, () => {
  page.value = 1
})
watch([page, pageSize, projectFilter], reload)

async function reload() {
  loading.value = true
  try {
    const data = await fetchFiles({
      projectId: projectFilter.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    files.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
    page.value = data.page
    pageSize.value = data.pageSize
  } catch {
    files.value = []
    total.value = 0
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

async function onUpload() {
  errorMsg.value = ''
  if (!pickedFile.value) {
    errorMsg.value = '请选择要上传的本地文件'
    return
  }
  submitting.value = true
  try {
    await uploadFile({
      projectId: form.projectId,
      name: form.name,
      kind: form.kind,
      file: pickedFile.value,
    })
    files.value = []
    closeUpload()
    page.value = 1
    await reload()
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page {
  display: grid;
  gap: 14px;
}

.toolbar {
  display: flex;
  gap: 10px;
}

.hint {
  margin: 0;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: rgba(78, 168, 222, 0.08);
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
}

select,
input {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 11px 12px;
  outline: none;
}

.toolbar select {
  min-width: 220px;
}

.primary,
.ghost {
  border-radius: 10px;
  padding: 10px 14px;
  border: 1px solid transparent;
}

.primary {
  background: var(--accent);
  color: #fff;
  font-weight: 600;
}

.ghost {
  background: transparent;
  border-color: var(--border);
  color: var(--text-muted);
}

.table-wrap,
.empty {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-card);
  box-shadow: var(--shadow);
}

.empty {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

.empty-inline {
  padding: 28px 14px;
  text-align: center;
  color: var(--text-muted);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

th {
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(15, 157, 142, 0.06);
}

tr:last-child td {
  border-bottom: none;
}

.name {
  font-weight: 600;
}

.muted {
  color: var(--text-muted);
  font-size: 12px;
}

.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.btn-mini {
  border-radius: 8px;
  padding: 5px 10px;
  border: 1px solid rgba(78, 168, 222, 0.28);
  background: rgba(78, 168, 222, 0.1);
  color: #1d6f9a;
  font-size: 12px;
  font-weight: 600;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--info);
  max-width: 220px;
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.tag[data-s='transferred'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.15);
}

.tag[data-s='checking'] {
  color: var(--warn);
  background: rgba(233, 196, 106, 0.15);
}

.tag[data-s='uploaded'] {
  color: var(--info);
  background: rgba(78, 168, 222, 0.15);
}

.tag[data-s='failed'] {
  color: var(--danger);
  background: rgba(231, 111, 81, 0.15);
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 50;
}

.modal {
  width: min(520px, 100%);
  display: grid;
  gap: 12px;
  padding: 22px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
}

.trace-modal {
  width: min(720px, 100%);
  max-height: min(86vh, 860px);
  overflow: auto;
}

.modal h3 {
  margin: 0;
}

.modal label {
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

.file-input {
  width: 100%;
  cursor: pointer;
}

.file-input::file-selector-button {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 8px 12px;
  margin-right: 10px;
  cursor: pointer;
}

.tip {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.gds-detail {
  white-space: pre-wrap;
  font-family: ui-monospace, monospace;
  font-size: 11px;
  max-height: 200px;
  overflow: auto;
  padding: 8px;
  background: var(--bg-panel);
  border-radius: 6px;
}

.trace-gds-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.trace {
  list-style: none;
  margin: 0;
  padding: 4px 0 8px;
  display: grid;
  gap: 0;
}

.trace li {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 12px;
  position: relative;
  padding-bottom: 16px;
}

.trace li:last-child {
  padding-bottom: 0;
}

.trace li::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 18px;
  bottom: 0;
  width: 2px;
  background: #d5e3ec;
}

.trace li:last-child::before {
  display: none;
}

.trace .dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: #fff;
  z-index: 1;
}

.trace .dot[data-s='done'] {
  background: #0f9d8e;
  border-color: #0f9d8e;
}

.trace .dot[data-s='current'] {
  background: #2b7de9;
  border-color: #2b7de9;
  box-shadow: 0 0 0 4px rgba(43, 125, 233, 0.16);
}

.trace .dot[data-s='rejected'],
.trace .dot[data-s='failed'] {
  background: #e76f51;
  border-color: #e76f51;
}

.trace .dot[data-s='skipped'],
.trace .dot[data-s='waiting'] {
  background: #e7eef3;
}

.trace-body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.trace-head {
  display: flex;
  gap: 8px;
  align-items: baseline;
  flex-wrap: wrap;
}

.trace-head em {
  font-style: normal;
  font-size: 12px;
  color: var(--text-muted);
}

.trace-body p {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  word-break: break-all;
}

.meta {
  display: grid;
  gap: 8px;
  margin: 0;
}

.meta div {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px;
  font-size: 13px;
}

.meta dt {
  color: var(--text-muted);
}

.meta dd {
  margin: 0;
  min-width: 0;
}

.meta code,
.wrap {
  word-break: break-all;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
