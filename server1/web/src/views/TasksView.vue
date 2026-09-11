<template>
  <div class="page">
    <p class="hint">
      任务管理跟踪每一次<strong>新增提交</strong>（项目 / 文件）的审批节点：发起人、审核人、当前节点和状态。
      未审核时发起人可催办或撤回，此时还不能去分发。催办后审核人登录即可在右上角铃铛看到未读消息。
      管理员审核通过后，提交人可点「流转」，到流转控制向服务器2发起分发。
      撤回后流转控制不再显示；重新提交后会再进待审。被驳回或分发失败也可以重新提交。
    </p>
    <div class="toolbar">
      <select v-model="typeFilter">
        <option value="">全部类型</option>
        <option value="project">新建项目</option>
        <option value="file">上传文件</option>
        <option value="task">处理作业</option>
      </select>
      <select v-model="statusFilter">
        <option value="">全部状态</option>
        <option value="pending">待审核</option>
        <option value="distributing">待分发</option>
        <option value="completed">已完成</option>
        <option value="rejected">已驳回</option>
        <option value="failed">分发失败</option>
        <option value="withdrawn">已撤回</option>
        <option value="deleted">已删除</option>
      </select>
    </div>

    <div class="table-wrap">
      <div v-if="loading" class="empty-inline">加载中…</div>
      <table v-else>
        <thead>
          <tr>
            <th>提交</th>
            <th>类型</th>
            <th>发起人</th>
            <th>审核人</th>
            <th>当前节点</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td>
              <div class="name">{{ t.title || t.fileName || t.projectName }}</div>
              <div class="sub">{{ t.projectName }} · <code>{{ t.id }}</code></div>
            </td>
            <td>{{ t.type }}</td>
            <td>{{ t.applyUser || t.createdBy || '—' }}</td>
            <td>{{ t.reviewUser || '—' }}</td>
            <td>
              <button type="button" class="node-link" @click="openDetail(t)">{{ t.currentNodeLabel || '查看流程图' }}</button>
            </td>
            <td><span class="tag" :data-s="t.status">{{ statusText(t.status) }}</span></td>
            <td>
              <div class="ops">
                <button type="button" class="btn-mini" @click="openDetail(t)">查看流程图</button>
                <button v-if="t.canUrge" type="button" class="btn-mini" :disabled="busyId === t.id" @click="onUrge(t)">
                  {{ busyId === t.id ? '催办中…' : '催办' }}
                </button>
                <RouterLink
                  v-if="canGoCirculate(t)"
                  class="btn-mini link"
                  :to="{ name: 'circulation', query: { circulationId: t.id } }"
                >
                  流转
                </RouterLink>
                <button v-if="t.canWithdraw" type="button" class="btn-mini" :disabled="busyId === t.id" @click="onWithdraw(t)">
                  撤回
                </button>
                <button v-if="t.canRetry" type="button" class="btn-mini" :disabled="busyId === t.id" @click="onRetry(t)">
                  重新提交
                </button>
                <button v-if="t.canDelete" type="button" class="btn-mini danger" :disabled="busyId === t.id" @click="onDelete(t)">
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !tasks.length" class="empty-inline">暂无提交流程</div>
      <PagerBar v-model:page="page" v-model:page-size="pageSize" :total="total" :total-pages="totalPages" :loading="loading" />
    </div>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="modal">
        <h3>{{ detail.title || detail.fileName || detail.projectName }}</h3>
        <p class="tip">{{ detail.type }} · 发起人 {{ detail.applyUser || '—' }} · 审核人 {{ detail.reviewUser || '未审核' }}</p>
        <div class="flow">
          <div v-for="(n, i) in detail.nodes || []" :key="n.key" class="flow-item">
            <div class="flow-node">
              <span class="dot" :data-s="n.state" />
              <strong>{{ n.label }}</strong>
              <em>{{ nodeStateText(n.state) }}</em>
              <span v-if="n.actor">{{ n.actor }}</span>
              <span v-if="n.time" class="muted">{{ n.time }}</span>
              <span v-if="n.remark" class="remark">{{ n.remark }}</span>
            </div>
            <i v-if="i < (detail.nodes?.length || 0) - 1" class="flow-line" :data-s="n.state" />
          </div>
        </div>
        <dl class="meta">
          <div><dt>当前节点</dt><dd>{{ detail.currentNodeLabel }}</dd></div>
          <div><dt>审核状态</dt><dd>{{ statusText(detail.status) }}</dd></div>
          <div><dt>催办次数</dt><dd>{{ detail.urgeCount || 0 }}{{ detail.lastUrgeAt ? `（最近 ${detail.lastUrgeAt}）` : '' }}</dd></div>
          <div><dt>意见</dt><dd>{{ detail.comment || '—' }}</dd></div>
        </dl>
        <div class="actions">
          <button v-if="detail.canUrge" type="button" class="primary" :disabled="busyId === detail.id" @click="onUrge(detail)">催办</button>
          <RouterLink v-if="canGoCirculate(detail)" class="ghost link-btn" :to="{ name: 'circulation', query: { circulationId: detail.id } }">去流转</RouterLink>
          <button v-if="detail.canWithdraw" type="button" class="ghost" :disabled="busyId === detail.id" @click="onWithdraw(detail)">撤回</button>
          <button v-if="detail.canRetry" type="button" class="primary" :disabled="busyId === detail.id" @click="onRetry(detail)">重新提交</button>
          <button type="button" class="ghost" @click="detail = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { deleteTask, fetchTasks, retryTask, urgeTask, withdrawTask } from '@/modules/task/api'
import PagerBar from '@/shared/PagerBar.vue'
import type { TaskItem } from '@/types'

const loading = ref(true)
const tasks = ref<TaskItem[]>([])
const total = ref(0)
const totalPages = ref(1)
const page = ref(1)
const pageSize = ref(10)
const typeFilter = ref('')
const statusFilter = ref('')
const busyId = ref('')
const errorMsg = ref('')
const detail = ref<TaskItem | null>(null)

function statusText(s?: string) {
  const map: Record<string, string> = {
    pending: '待审核',
    distributing: '待分发',
    completed: '已完成',
    rejected: '已驳回',
    failed: '分发失败',
    withdrawn: '已撤回',
    deleted: '已删除',
    waiting_review: '待审核',
    running: '进行中',
    approved: '已完成',
  }
  return map[s || ''] ?? s ?? '—'
}

function nodeStateText(s?: string) {
  const map: Record<string, string> = {
    done: '已完成',
    current: '进行中',
    waiting: '未到达',
    skipped: '已跳过',
    rejected: '已拒绝',
    failed: '失败',
  }
  return map[s || ''] ?? s ?? ''
}

function canGoCirculate(t: TaskItem) {
  return Boolean(t.canDistribute) || t.status === 'distributing' || t.status === 'failed'
}

function openDetail(t: TaskItem) {
  detail.value = t
}

async function reload() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await fetchTasks({
      applyType: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    tasks.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
    page.value = data.page
    pageSize.value = data.pageSize
    if (detail.value) {
      detail.value = tasks.value.find((item) => item.id === detail.value?.id) || detail.value
    }
  } catch (e) {
    tasks.value = []
    errorMsg.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function run(id: string, action: () => Promise<TaskItem>) {
  busyId.value = id
  errorMsg.value = ''
  try {
    const updated = await action()
    tasks.value = tasks.value.map((item) => (item.id === updated.id ? updated : item))
    if (detail.value?.id === updated.id) detail.value = updated
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busyId.value = ''
  }
}

function onUrge(t: TaskItem) {
  return run(t.id, () => urgeTask(t.id))
}
function onRetry(t: TaskItem) {
  return run(t.id, () => retryTask(t.id))
}
function onWithdraw(t: TaskItem) {
  if (!window.confirm('撤回后流转控制不再显示该单据，任务管理会保留为「已撤回」。确定撤回？')) return
  return run(t.id, () => withdrawTask(t.id))
}
function onDelete(t: TaskItem) {
  if (!window.confirm('删除后流转控制不再显示，任务管理会保留为「已删除」。确定删除？')) return
  return run(t.id, () => deleteTask(t.id))
}

onMounted(reload)
watch([typeFilter, statusFilter], () => {
  page.value = 1
})
watch(pageSize, () => {
  page.value = 1
})
watch([page, pageSize, typeFilter, statusFilter], reload)
</script>

<style scoped>
.page {
  display: grid;
  gap: 14px;
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
.toolbar {
  display: flex;
  gap: 10px;
}
select {
  min-width: 160px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 11px 12px;
}
.table-wrap {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-card);
  box-shadow: var(--shadow);
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
  vertical-align: middle;
}
th {
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(15, 157, 142, 0.06);
}
.name {
  font-weight: 600;
}
.sub {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.node-link,
.btn-mini {
  border-radius: 8px;
  padding: 5px 10px;
  border: 1px solid rgba(78, 168, 222, 0.28);
  background: rgba(78, 168, 222, 0.1);
  color: #1d6f9a;
  font-size: 12px;
  font-weight: 600;
}
.node-link {
  background: transparent;
  padding: 0;
  border: none;
  text-align: left;
  cursor: pointer;
}
.btn-mini.link {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn-mini.danger {
  color: var(--danger);
  border-color: rgba(231, 111, 81, 0.35);
  background: rgba(231, 111, 81, 0.08);
}
.btn-mini:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--bg-hover);
}
.tag[data-s='pending'],
.tag[data-s='waiting_review'] {
  color: var(--info);
  background: rgba(78, 168, 222, 0.15);
}
.tag[data-s='distributing'] {
  color: #a16207;
  background: rgba(233, 196, 106, 0.16);
}
.tag[data-s='completed'],
.tag[data-s='approved'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.15);
}
.tag[data-s='rejected'],
.tag[data-s='failed'],
.tag[data-s='deleted'] {
  color: var(--danger);
  background: rgba(231, 111, 81, 0.15);
}
.tag[data-s='withdrawn'] {
  color: var(--text-muted);
  background: rgba(143, 163, 184, 0.16);
}
.error {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 50;
}
.modal {
  width: min(720px, 100%);
  display: grid;
  gap: 14px;
  padding: 22px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
}
.modal h3 {
  margin: 0;
}
.tip {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}
.flow {
  display: flex;
  gap: 0;
  overflow-x: auto;
  padding: 8px 0 4px;
}
.flow-item {
  display: flex;
  align-items: stretch;
  min-width: 140px;
  flex: 1;
}
.flow-node {
  display: grid;
  gap: 4px;
  justify-items: center;
  text-align: center;
  font-size: 12px;
  min-width: 120px;
}
.flow-node strong {
  color: var(--text);
}
.flow-node em {
  font-style: normal;
  color: var(--text-muted);
}
.flow-node span,
.remark {
  color: var(--text-muted);
  line-height: 1.4;
}
.dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: #fff;
}
.dot[data-s='done'] {
  background: #0f9d8e;
  border-color: #0f9d8e;
}
.dot[data-s='current'] {
  background: #2b7de9;
  border-color: #2b7de9;
  box-shadow: 0 0 0 4px rgba(43, 125, 233, 0.16);
}
.dot[data-s='rejected'],
.dot[data-s='failed'] {
  background: #e76f51;
  border-color: #e76f51;
}
.dot[data-s='skipped'],
.dot[data-s='waiting'] {
  background: #e7eef3;
}
.flow-line {
  flex: 1;
  height: 2px;
  margin-top: 10px;
  background: #d5e3ec;
  min-width: 16px;
}
.flow-line[data-s='done'] {
  background: #0f9d8e;
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
dt {
  color: var(--text-muted);
}
dd {
  margin: 0;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
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
.link-btn {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.muted {
  color: var(--text-muted);
}
</style>
