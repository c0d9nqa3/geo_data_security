<template>
  <div class="page">
    <section class="hero-row">
      <div>
        <h2 class="page-title">安全工作台</h2>
        <p class="flow-line">数据导入 → 沙箱处理 → 水印嵌入 → 流转审计 → 链上追溯</p>
      </div>
      <RouterLink class="import-btn" to="/files">导入测绘数据</RouterLink>
    </section>

    <section class="stats">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <div class="label">{{ card.label }}</div>
        <div class="value">{{ card.value }}</div>
        <div class="meta">{{ card.meta }}</div>
      </article>
    </section>

    <section class="grid-2 fill">
      <div class="panel">
        <div class="panel-head">
          <h3>最近任务</h3>
          <RouterLink to="/tasks">查看全部</RouterLink>
        </div>
        <div v-if="!tasks.length" class="empty">暂无任务</div>
        <table v-else>
          <thead>
            <tr>
              <th>任务</th>
              <th>类型</th>
              <th>进度</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks.slice(0, 6)" :key="t.id">
              <td>
                <div class="name">{{ t.fileName }}</div>
                <div class="sub">{{ t.id }}</div>
              </td>
              <td>{{ t.type }}</td>
              <td>{{ t.progress }}%</td>
              <td><span class="tag" :data-s="t.status">{{ statusText(t.status) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h3>最新审计事件</h3>
          <RouterLink to="/audit">进入审计页</RouterLink>
        </div>
        <div v-if="!audits.length" class="empty">暂无审计事件</div>
        <ul v-else class="audit-list">
          <li v-for="e in audits.slice(0, 8)" :key="e.id">
            <div class="time">{{ e.time }}</div>
            <div>
              <strong>{{ e.action }}</strong>
              <p>{{ e.detail }}</p>
            </div>
            <span class="tag" :data-r="e.result">{{ resultText(e.result) }}</span>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAudits } from '@/modules/audit/api'
import { fetchFiles } from '@/modules/ingest/api'
import { fetchProjects } from '@/modules/project/api'
import { fetchTasks } from '@/modules/task/api'
import type { AuditEvent, TaskItem, TaskStatus } from '@/types'

const cards = ref([
  { label: '在管项目', value: '—', meta: '按项目隔离加密卷' },
  { label: '测绘文件', value: '—', meta: 'GeoTIFF / SHP / DLG / OSGB' },
  { label: '运行中任务', value: '—', meta: '水印 + 沙箱调度' },
  { label: '待处理告警', value: '—', meta: 'ElastAlert2 ≤ 10s' },
])

const tasks = ref<TaskItem[]>([])
const audits = ref<AuditEvent[]>([])

function statusText(s: TaskStatus) {
  return (
    {
      queued: '排队',
      running: '运行中',
      waiting_review: '待审核',
      approved: '成功',
      rejected: '驳回',
      failed: '失败',
    } as const
  )[s]
}

function resultText(r: AuditEvent['result']) {
  return ({ success: '成功', denied: '拒绝', error: '错误' } as const)[r]
}

onMounted(async () => {
  const [projects, files, taskList, auditList] = await Promise.all([
    fetchProjects(),
    fetchFiles(),
    fetchTasks(),
    fetchAudits(),
  ])
  tasks.value = taskList
  audits.value = auditList
  const running = taskList.filter((t) => t.status === 'running' || t.status === 'queued').length
  const alerts = auditList.filter((e) => e.result === 'denied' || e.result === 'error').length
  cards.value = [
    { label: '在管项目', value: String(projects.length), meta: '按项目隔离加密卷' },
    { label: '测绘文件', value: String(files.length), meta: 'GeoTIFF / SHP / DLG / OSGB' },
    { label: '运行中任务', value: String(running), meta: '水印 + 沙箱调度' },
    { label: '待处理告警', value: String(alerts), meta: 'ElastAlert2 ≤ 10s' },
  ]
})
</script>

<style scoped>
.page {
  display: grid;
  gap: 18px;
  min-height: calc(100vh - 120px);
  grid-template-rows: auto auto 1fr;
}

.hero-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.flow-line {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 13px;
}

.import-btn {
  display: inline-flex;
  align-items: center;
  border-radius: 10px;
  padding: 10px 16px;
  background: linear-gradient(135deg, var(--accent), #3a86ff);
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card,
.panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: rgba(28, 37, 48, 0.88);
}

.stat-card {
  padding: 18px 18px 16px;
}

.label {
  color: var(--text-muted);
  font-size: 13px;
}

.value {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 700;
}

.meta {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.fill > .panel {
  min-height: 360px;
  height: 100%;
}

.panel {
  padding: 16px 18px 18px;
  display: flex;
  flex-direction: column;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-head h3 {
  margin: 0;
  font-size: 16px;
}

.panel-head a {
  color: var(--accent-hover);
  font-size: 13px;
}

.empty {
  color: var(--text-muted);
  padding: 28px 0;
  text-align: center;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  font-size: 13px;
}

th {
  color: var(--text-muted);
  font-weight: 600;
  font-size: 12px;
}

.name {
  font-weight: 600;
}

.sub {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.audit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.audit-list li {
  display: grid;
  grid-template-columns: 88px 1fr auto;
  gap: 10px;
  align-items: start;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.audit-list .time {
  color: var(--text-muted);
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.audit-list p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.45;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--bg-hover);
}

.tag[data-s='approved'],
.tag[data-r='success'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.15);
}

.tag[data-s='running'],
.tag[data-s='queued'] {
  color: var(--info);
  background: rgba(78, 168, 222, 0.15);
}

.tag[data-s='waiting_review'],
.tag[data-r='denied'] {
  color: var(--warn);
  background: rgba(233, 196, 106, 0.15);
}

.tag[data-s='failed'],
.tag[data-s='rejected'],
.tag[data-r='error'] {
  color: var(--danger);
  background: rgba(231, 111, 81, 0.15);
}

@media (max-width: 1100px) {
  .stats,
  .grid-2 {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .stats,
  .grid-2,
  .audit-list li {
    grid-template-columns: 1fr;
  }

  .hero-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
