<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="projectFilter">
        <option value="">全部项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <button type="button" class="primary" @click="showUpload = true">上传数据</button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else class="table-wrap">
      <table>
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
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in filtered" :key="f.id">
            <td class="name">{{ f.name }}</td>
            <td>{{ f.kind }}</td>
            <td>{{ f.projectName }}</td>
            <td>{{ f.sizeMb }} MB</td>
            <td><span class="tag" :data-s="f.status">{{ statusText(f.status) }}</span></td>
            <td><code>{{ f.hash }}</code></td>
            <td>{{ f.uploadedBy }}</td>
            <td>{{ f.uploadedAt }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showUpload" class="modal-mask" @click.self="showUpload = false">
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
          文件名
          <input v-model="form.name" required placeholder="例如：tile_B01.tif" />
        </label>
        <p class="tip">真实环境由 ingest 模块接收、校验并转交服务器2；此处仅模拟上传记录。</p>
        <div class="actions">
          <button type="button" class="ghost" @click="showUpload = false">取消</button>
          <button type="submit" class="primary">模拟上传</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchFiles, fetchProjects } from '@/api/client'
import type { DataFile, FileKind, Project } from '@/types'

const loading = ref(true)
const files = ref<DataFile[]>([])
const projects = ref<Project[]>([])
const projectFilter = ref('')
const showUpload = ref(false)
const form = reactive({
  projectId: '',
  kind: 'GeoTIFF' as FileKind,
  name: '',
})

const filtered = computed(() =>
  projectFilter.value ? files.value.filter((f) => f.projectId === projectFilter.value) : files.value,
)

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

onMounted(async () => {
  ;[projects.value, files.value] = await Promise.all([fetchProjects(), fetchFiles()])
  loading.value = false
})

function onUpload() {
  const project = projects.value.find((p) => p.id === form.projectId)
  if (!project) return
  const now = new Date()
  const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  files.value = [
    {
      id: `file_${Date.now()}`,
      projectId: project.id,
      projectName: project.name,
      name: form.name,
      kind: form.kind,
      sizeMb: Math.round(Math.random() * 800 + 20),
      status: 'uploaded',
      hash: `sha256:${Math.random().toString(16).slice(2, 6)}…`,
      uploadedBy: '当前用户',
      uploadedAt: stamp,
    },
    ...files.value,
  ]
  form.name = ''
  form.projectId = ''
  showUpload.value = false
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
  background: rgba(28, 37, 48, 0.88);
}

.empty {
  padding: 40px;
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
}

tr:last-child td {
  border-bottom: none;
}

.name {
  font-weight: 600;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--info);
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
  width: min(460px, 100%);
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
