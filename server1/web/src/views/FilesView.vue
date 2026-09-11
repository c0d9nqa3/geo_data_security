<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="projectFilter">
        <option value="">全部项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <button type="button" class="primary" @click="showUpload = true">上传数据</button>
    </div>
    <p class="hint">{{ reviewer ? '管理员可查看全部上传文件。' : '你只能看到自己上传的文件，入库后可发起处理作业。' }}</p>

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
            <th>哈希</th>
            <th>上传人</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.id">
            <td class="name">{{ f.name }}</td>
            <td>{{ f.kind }}</td>
            <td>{{ f.projectName }}</td>
            <td>{{ f.sizeMb }} MB</td>
            <td><span class="tag" :data-s="f.status">{{ statusText(f.status) }}</span></td>
            <td><code>{{ f.hash }}</code></td>
            <td>{{ f.uploadedBy }}</td>
            <td>{{ f.uploadedAt }}</td>
            <td>
              <button
                v-if="f.status === 'transferred'"
                type="button"
                class="btn-mini"
                @click="startProcess(f.id)"
              >
                发起处理
              </button>
              <span v-else class="muted">入库后可处理</span>
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
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
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
            <option>GeoTIFF</option>
            <option>SHP/GeoJSON</option>
            <option>DLG</option>
            <option>OSGB</option>
            <option>其他</option>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchFiles, uploadFile } from '@/modules/ingest/api'
import { fetchProjects } from '@/modules/project/api'
import { canReview } from '@/shared/access'
import PagerBar from '@/shared/PagerBar.vue'
import type { DataFile, FileKind, Project } from '@/types'

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
const form = reactive({
  projectId: '',
  kind: 'GeoTIFF' as FileKind,
  name: '',
})

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

function startProcess(fileId: string) {
  router.push({ name: 'tasks', query: { fileId } })
}

function inferKind(name: string): FileKind {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'tif' || ext === 'tiff') return 'GeoTIFF'
  if (ext === 'shp' || ext === 'geojson' || ext === 'json') return 'SHP/GeoJSON'
  if (ext === 'dlg') return 'DLG'
  if (ext === 'osgb') return 'OSGB'
  return '其他'
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
  try {
    const projectPage = await fetchProjects({ page: 1, pageSize: 100 })
    projects.value = projectPage.items
  } catch {
    projects.value = []
  }
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

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
