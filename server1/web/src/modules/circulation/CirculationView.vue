<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="statusFilter">
        <option value="">全部状态</option>
        <option value="pending">待办</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
      </select>
    </div>
    <p class="hint">
      在「项目管理 / 文件管理 / 任务管理」提交后，这里自动出现待办。待办仅管理员可见；列表可直接通过或拒绝，通过后在右侧提交分发授权。
    </p>

    <div class="layout">
      <div class="list-col">
        <div v-if="loading" class="empty">加载中…</div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>类型</th>
                <th>项目 / 对象</th>
                <th>申请人</th>
                <th>状态</th>
                <th>分发</th>
                <th v-if="canReview">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in items"
                :key="item.id"
                :class="{ selected: selectedId === item.id }"
                @click="selectRow(item.id)"
              >
                <td>
                  <span class="type-pill" :data-t="item.applyType || 'task'">{{ typeText(item.applyType) }}</span>
                </td>
                <td>
                  <div class="name">{{ item.projectName }}</div>
                  <div class="sub">{{ objectText(item) }}</div>
                </td>
                <td>{{ item.applyUser }}</td>
                <td><span class="tag" :data-s="item.status">{{ statusText(item.status) }}</span></td>
                <td>
                  <span class="dist-pill" :data-d="item.distributeStatus">{{ distributeText(item.distributeStatus) }}</span>
                </td>
                <td v-if="canReview">
                  <div v-if="item.status === 'pending'" class="ops">
                    <button type="button" class="btn-pass" :disabled="busy" @click.stop="onApprove(item.id)">通过</button>
                    <button type="button" class="btn-reject" :disabled="busy" @click.stop="onReject(item.id)">拒绝</button>
                  </div>
                  <span v-else class="muted-inline">—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!items.length" class="empty-inline">
            {{ canReview ? '暂无流转待办' : '暂无已处理单据。你提交的待办仅管理员可见。' }}
          </div>
          <div class="pager">
            <div class="pager-meta">
              共 <strong>{{ total }}</strong> 条 · 共 <strong>{{ totalPages }}</strong> 页
            </div>
            <label class="pager-size">
              每页
              <select v-model.number="pageSize">
                <option :value="5">5</option>
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
              </select>
              条
            </label>
            <div class="pager-nav">
              <button type="button" class="btn-page" :disabled="page <= 1 || loading" @click="page = page - 1">上一页</button>
              <span class="pager-now">第 {{ page }} / {{ totalPages }} 页</span>
              <button type="button" class="btn-page" :disabled="page >= totalPages || loading" @click="page = page + 1">下一页</button>
            </div>
            <form class="pager-jump" @submit.prevent="goJump">
              跳至
              <input v-model.number="jumpPage" type="number" min="1" :max="totalPages" />
              页
              <button type="submit" class="btn-page">确定</button>
            </form>
          </div>
        </div>
      </div>

      <aside v-if="selected" class="detail">
        <p class="sheet-kicker">流转明细</p>
        <h3>{{ typeText(selected.applyType) }} · {{ selected.projectName }}</h3>
        <dl>
          <div><dt>流转单</dt><dd><code>{{ selected.id }}</code></dd></div>
          <div><dt>类型</dt><dd>{{ typeText(selected.applyType) }}</dd></div>
          <div><dt>项目</dt><dd>{{ selected.projectName }}</dd></div>
          <div><dt>文件</dt><dd>{{ selected.fileName || selected.fileId || '—' }}</dd></div>
          <div><dt>任务</dt><dd>{{ selected.taskId || '—' }}</dd></div>
          <div><dt>用途</dt><dd>{{ selected.purpose || '—' }}</dd></div>
          <div><dt>授权范围</dt><dd>{{ scopeText(selected.authorizeScope) }}</dd></div>
          <div><dt>授权截止</dt><dd>{{ selected.expireAt || '—' }}</dd></div>
          <div><dt>申请人</dt><dd>{{ selected.applyUser }}</dd></div>
          <div><dt>审批人</dt><dd>{{ selected.reviewUser || '—' }}</dd></div>
          <div><dt>审批意见</dt><dd>{{ selected.comment || '—' }}</dd></div>
          <div>
            <dt>状态</dt>
            <dd><span class="tag" :data-s="selected.status">{{ statusText(selected.status) }}</span></dd>
          </div>
          <div>
            <dt>分发</dt>
            <dd>
              <span class="dist-pill" :data-d="selected.distributeStatus">
                {{ distributeText(selected.distributeStatus) }}
              </span>
            </dd>
          </div>
        </dl>
        <button
          v-if="canReview && selected.status === 'approved' && selected.distributeStatus !== 'dispatched'"
          type="button"
          class="btn-auth"
          :disabled="busy"
          @click="onDistribute(selected.id)"
        >
          提交分发授权
        </button>
      </aside>
    </div>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  approveCirculation,
  distributeCirculation,
  fetchCirculations,
  rejectCirculation,
} from '@/modules/circulation/api'
import { getStoredUser } from '@/modules/auth/api'
import type { CirculationItem } from '@/types'

const user = getStoredUser()
const canReview = computed(() => {
  const perms = user?.permissions ?? []
  return perms.includes('review') || user?.role === 'admin'
})

const loading = ref(true)
const items = ref<CirculationItem[]>([])
const total = ref(0)
const totalPages = ref(1)
const page = ref(1)
const pageSize = ref(10)
const jumpPage = ref(1)
const statusFilter = ref('')
const selectedId = ref('')
const busy = ref(false)
const errorMsg = ref('')

const selected = computed(() => items.value.find((i) => i.id === selectedId.value) || null)

function typeText(type?: string) {
  if (type === 'project') return '新建项目'
  if (type === 'file') return '上传文件'
  return '提交任务'
}
function objectText(item: CirculationItem) {
  return item.fileName || item.taskId || item.purpose || item.id
}
function statusText(s: CirculationItem['status']) {
  return ({ pending: '待办', approved: '已通过', rejected: '已驳回' } as const)[s]
}
function scopeText(scope: string) {
  return scope === 'project_members' ? '项目成员' : '申请人本人'
}
function distributeText(s: string) {
  return s === 'dispatched' ? '已提交授权' : '未分发'
}

function selectRow(id: string) {
  selectedId.value = id
}

function goJump() {
  const target = Number(jumpPage.value)
  if (!Number.isFinite(target)) return
  page.value = Math.min(Math.max(1, Math.trunc(target)), totalPages.value)
}

async function reload() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await fetchCirculations({
      status: statusFilter.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    items.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
    page.value = data.page
    pageSize.value = data.pageSize
    jumpPage.value = data.page
    if (selectedId.value && !items.value.some((i) => i.id === selectedId.value)) {
      selectedId.value = items.value[0]?.id || ''
    } else if (!selectedId.value) {
      selectedId.value = items.value[0]?.id || ''
    }
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(reload)
watch(statusFilter, () => {
  page.value = 1
})
watch(pageSize, () => {
  page.value = 1
})
watch([page, pageSize, statusFilter], reload)

function patchItem(updated: CirculationItem) {
  items.value = items.value.map((i) => (i.id === updated.id ? updated : i))
}

async function onApprove(id: string) {
  selectedId.value = id
  busy.value = true
  errorMsg.value = ''
  try {
    patchItem(await approveCirculation(id, '审核通过'))
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    busy.value = false
  }
}

async function onReject(id: string) {
  selectedId.value = id
  busy.value = true
  errorMsg.value = ''
  try {
    patchItem(await rejectCirculation(id, '审核拒绝'))
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '拒绝失败'
  } finally {
    busy.value = false
  }
}

async function onDistribute(id: string) {
  busy.value = true
  errorMsg.value = ''
  try {
    patchItem(await distributeCirculation(id))
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '分发失败'
  } finally {
    busy.value = false
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
  align-items: center;
}
.hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.85fr);
  gap: 14px;
  align-items: start;
}
.list-col {
  min-width: 0;
}
select,
input {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 8px 10px;
}
select {
  min-width: 140px;
}
.table-wrap,
.empty,
.detail {
  border: 1px solid rgba(78, 168, 222, 0.16);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(32, 44, 56, 0.94), rgba(22, 30, 40, 0.92));
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.22);
}
.empty,
.empty-inline {
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
  padding: 13px 14px;
  text-align: left;
  border-bottom: 1px solid rgba(44, 58, 74, 0.85);
  vertical-align: middle;
}
th {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: rgba(15, 22, 30, 0.35);
}
tbody tr {
  cursor: pointer;
}
tbody tr.selected,
tbody tr:hover {
  background: rgba(42, 157, 143, 0.1);
}
.name {
  font-weight: 600;
}
.sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}
.ops {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.muted-inline {
  color: var(--text-muted);
  font-size: 12px;
}
.type-pill,
.dist-pill,
.tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.type-pill[data-t='project'] {
  color: #7dd3c7;
  background: rgba(42, 157, 143, 0.16);
}
.type-pill[data-t='file'] {
  color: #8ecae6;
  background: rgba(78, 168, 222, 0.16);
}
.type-pill[data-t='task'] {
  color: #f4d58d;
  background: rgba(233, 196, 106, 0.16);
}
.tag[data-s='pending'] {
  color: var(--warn);
  background: rgba(233, 196, 106, 0.16);
}
.tag[data-s='approved'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.18);
}
.tag[data-s='rejected'] {
  color: #ff8a70;
  background: rgba(231, 111, 81, 0.16);
}
.dist-pill[data-d='dispatched'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.16);
}
.dist-pill[data-d='none'] {
  color: var(--text-muted);
  background: rgba(143, 163, 184, 0.12);
}
.btn-pass,
.btn-reject,
.btn-auth,
.btn-page {
  border-radius: 8px;
  padding: 6px 12px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 600;
}
.btn-pass {
  background: var(--ok);
  color: #082016;
}
.btn-reject {
  background: transparent;
  border-color: rgba(231, 111, 81, 0.5);
  color: #ff9b84;
}
.btn-page {
  background: rgba(78, 168, 222, 0.1);
  border-color: rgba(78, 168, 222, 0.28);
  color: #9fd4f0;
}
.btn-auth {
  width: 100%;
  padding: 12px 16px;
  font-size: 14px;
  background: linear-gradient(135deg, #2a9d8f, #34b3a3);
  color: #07221e;
  box-shadow: 0 8px 20px rgba(42, 157, 143, 0.28);
}
.btn-pass:disabled,
.btn-reject:disabled,
.btn-auth:disabled,
.btn-page:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.detail {
  padding: 18px 20px 20px;
}
.sheet-kicker {
  margin: 0 0 4px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #7dd3c7;
}
.detail h3 {
  margin: 0 0 14px;
  font-size: 16px;
}
.detail dl {
  display: grid;
  gap: 10px;
  margin: 0 0 16px;
}
.detail dl div {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px;
  font-size: 13px;
}
dt {
  color: var(--text-muted);
}
dd {
  margin: 0;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #9fd4f0;
}
.pager {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: center;
  padding: 12px 14px;
  border-top: 1px solid rgba(44, 58, 74, 0.85);
  color: var(--text-muted);
  font-size: 13px;
}
.pager-meta strong {
  color: var(--text);
}
.pager-size,
.pager-jump {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pager-size select,
.pager-jump input {
  width: 72px;
  min-width: 0;
  padding: 6px 8px;
}
.pager-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pager-now {
  min-width: 88px;
  text-align: center;
}
.error {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}
@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
