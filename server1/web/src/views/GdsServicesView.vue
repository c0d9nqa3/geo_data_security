<template>
  <div class="gds-simple">
    <header class="gds-hero">
      <p class="gds-eyebrow">GDS · CORE</p>
      <h2>安全服务</h2>
      <p>
        以每次上传的文件夹（上传包）为最小单位，查看服务器2水印/沙箱处理状态；导出与下载直接在列表操作列完成。
      </p>
    </header>

    <section class="gds-panel">
      <p class="gds-hint">默认分页展示全部上传包。可按名称、项目、流转状态筛选；已转服务器2的会自动同步处理状态。</p>
      <div class="gds-filters">
        <label>上传包名称<input v-model="filters.name" placeholder="支持模糊匹配" @keyup.enter="onSearch" /></label>
        <label>项目
          <select v-model="filters.projectId">
            <option value="">全部项目</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name || p.code || p.id }}</option>
          </select>
        </label>
        <label>流转状态
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option value="uploaded">已接入</option>
            <option value="checking">校验中</option>
            <option value="transferred">已转服务器2</option>
            <option value="failed">失败</option>
          </select>
        </label>
        <div class="gds-actions">
          <button class="primary" type="button" :disabled="busy" @click="onSearch">查询</button>
          <button type="button" :disabled="busy" @click="resetFilters">重置</button>
        </div>
      </div>

      <div class="gds-table-wrap">
        <div v-if="busy && !rows.length" class="gds-empty">加载中…</div>
        <table v-else class="gds-table">
          <thead>
            <tr>
              <th>上传包</th>
              <th>项目</th>
              <th>流转状态</th>
              <th>处理状态</th>
              <th>水印/沙箱</th>
              <th>结果编号</th>
              <th>导出</th>
              <th>下载</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in displayRows" :key="row.id">
              <td>
                <div class="name">{{ row.name }}</div>
                <code>{{ row.id }}</code>
              </td>
              <td>{{ row.projectName || row.projectId }}</td>
              <td><span class="gds-tag" :class="statusTone(row.status)">{{ statusText(row.status) }}</span></td>
              <td><span class="gds-tag" :class="processTone(row)">{{ processText(row) }}</span></td>
              <td>{{ row.processHint || '—' }}</td>
              <td><code>{{ row.resultId || '—' }}</code></td>
              <td>
                <div class="gds-ops">
                  <button class="primary" type="button" :disabled="busy || !row.resultId || row.acting" @click="exportZip(row)">导出 ZIP</button>
                  <button type="button" :disabled="busy || !row.resultId || row.acting" @click="exportManifest(row)">导出清单</button>
                </div>
              </td>
              <td>
                <div class="gds-ops">
                  <button type="button" :disabled="busy || !row.resultId || row.acting" @click="downloadPack(row)">下载</button>
                  <button type="button" :disabled="busy || row.acting" @click="refreshOne(row)">刷新</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!busy && !displayRows.length" class="gds-empty">没有匹配的上传包</div>
      </div>

      <PagerBar
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :total-pages="totalPages"
        :loading="busy"
      />
    </section>

    <p v-if="msg" class="gds-msg" :class="msgType">{{ msg }}</p>
    <p v-if="err" class="gds-err">{{ err }}</p>
  </div>
</template>

<script setup lang="ts">
import {
  downloadGdsExportZip,
  downloadGdsResultExportCompat,
  fetchFileGdsContext,
  fetchFileGdsManifest,
  fetchFileGdsVerification,
  fetchGdsExportJob,
  postFileGdsExport,
} from '@/modules/gds/api'
import { fetchFiles } from '@/modules/ingest/api'
import { fetchAllProjects } from '@/modules/project/api'
import PagerBar from '@/shared/PagerBar.vue'
import type { DataFile, Project } from '@/types'
import { computed, onMounted, reactive, ref, watch } from 'vue'

type Row = DataFile & {
  resultId?: string
  taskId?: string
  processHint?: string
  hasResult?: boolean
  acting?: boolean
}

const busy = ref(false)
const err = ref('')
const msg = ref('')
const msgType = ref<'ok' | 'info'>('info')
const projects = ref<Project[]>([])
const rows = ref<Row[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const totalPages = ref(1)
const filters = reactive({ name: '', projectId: '', status: '' })
const nameQuery = ref('')

const displayRows = computed(() => {
  const q = nameQuery.value.trim().toLowerCase()
  let list = rows.value
  if (filters.status) list = list.filter((r) => r.status === filters.status)
  if (q) list = list.filter((r) => r.name.toLowerCase().includes(q) || r.id.toLowerCase().includes(q))
  return list
})

function statusText(s: string) {
  return ({ uploaded: '已接入', checking: '校验中', transferred: '已转服务器2', failed: '失败' } as Record<string, string>)[s] || s
}
function statusTone(s: string) {
  if (s === 'failed') return 'danger'
  if (s === 'checking') return 'warn'
  if (s === 'transferred') return ''
  return 'muted'
}
function processText(row: Row) {
  if (row.hasResult) return '处理完成'
  if (row.status === 'transferred') return '处理中/待同步'
  if (row.status === 'failed') return '失败'
  return '未处理'
}
function processTone(row: Row) {
  if (row.hasResult) return ''
  if (row.status === 'failed') return 'danger'
  if (row.status === 'transferred') return 'warn'
  return 'muted'
}

async function run(label: string, fn: () => Promise<unknown>, okText?: string) {
  busy.value = true
  err.value = ''
  msg.value = '正在' + label + '…'
  msgType.value = 'info'
  try {
    const data = await fn()
    msg.value = okText || (label + '完成')
    msgType.value = 'ok'
    return data
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
    msg.value = ''
    return undefined
  } finally {
    busy.value = false
  }
}

async function enrich(row: Row) {
  try {
    const ctx = (await fetchFileGdsContext(row.id)) as Record<string, unknown>
    row.resultId = String(ctx.server2ResultId || ctx.resultId || '')
    row.taskId = String(ctx.server2TaskId || ctx.taskId || '')
    row.hasResult = Boolean(row.resultId)
    if (!row.resultId) {
      row.processHint = row.status === 'transferred' ? '已分发，等待结果' : '—'
      return
    }
    try {
      const ver = (await fetchFileGdsVerification(row.id)) as Record<string, unknown>
      const wm = ver.watermark ?? ver.watermark_text ?? ver.watermarkText
      row.processHint = wm ? '含水印 · 沙箱完成' : '沙箱完成'
    } catch {
      row.processHint = '已有结果'
    }
  } catch {
    row.hasResult = false
    row.processHint = row.status === 'transferred' ? '已分发，尚未关联结果' : '—'
  }
}

async function reload() {
  busy.value = true
  err.value = ''
  msg.value = '正在加载上传包…'
  msgType.value = 'info'
  try {
    const data = await fetchFiles({
      projectId: filters.projectId || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    rows.value = data.items.map((f) => ({ ...f }))
    total.value = data.total
    totalPages.value = data.totalPages
    page.value = data.page
    pageSize.value = data.pageSize

    const targets = rows.value.filter((r) => r.status === 'transferred' || r.status === 'checking')
    const queue = targets.length ? targets : rows.value.slice(0, 8)
    let i = 0
    await Promise.all(
      Array.from({ length: Math.min(5, queue.length) }, async () => {
        while (i < queue.length) {
          const cur = queue[i++]
          await enrich(cur)
        }
      }),
    )
    msg.value = '列表已更新'
    msgType.value = 'ok'
  } catch (e) {
    rows.value = []
    total.value = 0
    totalPages.value = 1
    err.value = e instanceof Error ? e.message : String(e)
    msg.value = ''
  } finally {
    busy.value = false
  }
}

function onSearch() {
  nameQuery.value = filters.name
  page.value = 1
  reload()
}

function resetFilters() {
  filters.name = ''
  filters.projectId = ''
  filters.status = ''
  nameQuery.value = ''
  page.value = 1
  reload()
}

async function refreshOne(row: Row) {
  row.acting = true
  try {
    await enrich(row)
    msg.value = '状态已刷新'
    msgType.value = 'ok'
    err.value = ''
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    row.acting = false
  }
}

async function exportZip(row: Row) {
  if (!row.resultId) {
    err.value = '该上传包尚无服务器2结果，不能导出'
    return
  }
  row.acting = true
  busy.value = true
  err.value = ''
  msg.value = '正在创建导出…'
  msgType.value = 'info'
  try {
    const data = (await postFileGdsExport(row.id)) as Record<string, unknown>
    const exportId = String(data.export_id || data.exportId || '')
    if (!exportId) throw new Error('未返回导出任务编号')
    // 轻量轮询几次再下载
    for (let n = 0; n < 5; n++) {
      const job = (await fetchGdsExportJob(exportId)) as Record<string, unknown>
      const st = String(job.status || job.state || '').toLowerCase()
      if (!st || st.includes('done') || st.includes('success') || st.includes('ready') || st.includes('complete')) break
      await new Promise((r) => setTimeout(r, 800))
    }
    await downloadGdsExportZip(exportId)
    msg.value = 'ZIP 已开始下载'
    msgType.value = 'ok'
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
    msg.value = ''
  } finally {
    row.acting = false
    busy.value = false
  }
}

async function exportManifest(row: Row) {
  if (!row.resultId) {
    err.value = '该上传包尚无服务器2结果，不能导出清单'
    return
  }
  row.acting = true
  try {
    const data = await fetchFileGdsManifest(row.id)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.name.replace(/\.[^.]+$/, '') + '-manifest.json'
    a.click()
    URL.revokeObjectURL(url)
    msg.value = '清单 JSON 已下载'
    msgType.value = 'ok'
    err.value = ''
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    row.acting = false
  }
}

async function downloadPack(row: Row) {
  if (!row.resultId) {
    // 尝试先刷新拿结果号
    await enrich(row)
  }
  if (!row.resultId) {
    err.value = '该上传包尚无服务器2结果，不能下载'
    return
  }
  row.acting = true
  busy.value = true
  err.value = ''
  msg.value = '正在下载…'
  msgType.value = 'info'
  try {
    await downloadGdsResultExportCompat(row.resultId)
    msg.value = '已触发下载'
    msgType.value = 'ok'
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
    msg.value = ''
  } finally {
    row.acting = false
    busy.value = false
  }
}

let ready = false
watch(pageSize, () => {
  page.value = 1
})
watch([page, pageSize], () => {
  if (!ready) return
  reload()
})
watch(
  () => filters.projectId,
  () => {
    if (!ready) return
    page.value = 1
    reload()
  },
)

onMounted(async () => {
  try {
    projects.value = await fetchAllProjects()
  } catch {
    projects.value = []
  }
  await reload()
  ready = true
})

</script>
