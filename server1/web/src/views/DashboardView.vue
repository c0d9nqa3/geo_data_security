<template>
  <div class="dash">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">GEO SECURITY · COMMAND CENTER</p>
        <h2>测绘数据安全工作台</h2>
        <p class="lead">全平台态势一眼看清：导入、处理、流转、审计同步汇聚，覆盖最近七天脉搏。</p>
        <div class="pipeline">
          <span>数据导入</span><i />
          <span>沙箱处理</span><i />
          <span>水印嵌入</span><i />
          <span>流转审计</span><i />
          <span>链上追溯</span>
        </div>
      </div>
      <div class="hero-side">
        <div class="scan-orb" aria-hidden="true" />
        <RouterLink class="import-btn" to="/files">导入测绘数据</RouterLink>
        <p class="hint-all">统计、任务曲线、审计曲线与列表对所有登录用户开放，展示全平台数据。</p>
      </div>
    </section>

    <section class="stats">
      <article v-for="card in cards" :key="card.label" class="stat-card" :data-tone="card.tone">
        <div class="stat-top">
          <span class="label">{{ card.label }}</span>
          <span class="pulse" />
        </div>
        <div class="value">{{ card.value }}</div>
        <div class="meta">{{ card.meta }}</div>
      </article>
    </section>

    <DataVolumePanel />

    <section class="charts">
      <article class="glass">
        <TrendChart title="提交流程" color="#0f9d8e" unit="条流程" :points="taskTrend" />
      </article>
      <article class="glass">
        <TrendChart title="审计事件" color="#2b7de9" unit="条事件" :points="auditTrend" />
      </article>
    </section>

    <section class="boards">
      <article class="glass board">
        <div class="panel-head">
          <div>
            <p class="kicker">LIVE FEED</p>
            <h3>最新任务</h3>
          </div>
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
            <tr v-for="t in tasks.slice(0, 8)" :key="t.id">
              <td>
                <div class="name">{{ t.title || t.fileName || t.id }}</div>
                <div class="sub">{{ t.id }}</div>
              </td>
              <td>{{ t.type }}</td>
              <td>
                <div class="bar"><i :style="{ width: `${t.progress || 0}%` }" /></div>
              </td>
              <td><span class="tag" :data-s="t.status">{{ statusText(t.status) }}</span></td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="glass board">
        <div class="panel-head">
          <div>
            <p class="kicker">TRACE STREAM</p>
            <h3>最新审计事件</h3>
          </div>
          <RouterLink to="/audit">进入审计页</RouterLink>
        </div>
        <div v-if="!audits.length" class="empty">暂无审计事件</div>
        <ul v-else class="audit-list">
          <li v-for="e in audits.slice(0, 8)" :key="e.id">
            <div class="time">{{ shortTime(e.time) }}</div>
            <div>
              <strong>{{ actionText(e.action) }}</strong>
              <p>{{ e.detail }}</p>
            </div>
            <span class="tag" :data-r="e.result">{{ resultText(e.result) }}</span>
          </li>
        </ul>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchDashboardOverview, type DashboardTrendPoint } from '@/modules/dashboard/api'
import TrendChart from '@/shared/TrendChart.vue'
import DataVolumePanel from '@/shared/DataVolumePanel.vue'
import type { AuditEvent, TaskItem } from '@/types'

const cards = ref([
  { label: '在管项目', value: '—', meta: '全平台项目总数', tone: 'teal' },
  { label: '测绘文件', value: '—', meta: '全平台已上传文件', tone: 'blue' },
  { label: '运行中任务', value: '—', meta: '待审核 / 待分发', tone: 'cyan' },
  { label: '待处理告警', value: '—', meta: '审计拒绝与错误', tone: 'amber' },
])

const tasks = ref<TaskItem[]>([])
const audits = ref<AuditEvent[]>([])
const taskTrend = ref<DashboardTrendPoint[]>([])
const auditTrend = ref<DashboardTrendPoint[]>([])

function statusText(s: string) {
  return (
    {
      queued: '排队',
      running: '运行中',
      waiting_review: '待审核',
      pending: '待审核',
      distributing: '待分发',
      completed: '已完成',
      approved: '成功',
      rejected: '驳回',
      failed: '失败',
      withdrawn: '已撤回',
      deleted: '已删除',
    } as Record<string, string>
  )[s] ?? s
}

function actionText(a: AuditEvent['action'] | string) {
  const map: Record<string, string> = {
    upload: '上传',
    create_project: '创建项目',
    submit_task: '提交任务',
    approve: '审批',
    reject: '驳回',
    apply_circulation: '流转申请',
    distribute: '分发授权',
    delete_circulation: '删除流转单',
    download_result: '结果下载',
    process_complete: '处理完成',
    query_trace: '追溯查询',
    urge: '催办',
    resubmit: '重新提交',
    withdraw: '撤回',
  }
  return map[a] ?? a
}

function resultText(r: AuditEvent['result']) {
  return ({ success: '成功', denied: '拒绝', error: '错误' } as const)[r]
}

function shortTime(value?: string) {
  if (!value) return '—'
  return value.length > 11 ? value.slice(5) : value
}

onMounted(async () => {
  try {
    const overview = await fetchDashboardOverview()
    tasks.value = overview.recentTasks || []
    audits.value = overview.recentAudits || []
    taskTrend.value = overview.taskTrend || []
    auditTrend.value = overview.auditTrend || []
    cards.value = [
      { label: '在管项目', value: String(overview.projectCount), meta: '全平台项目总数', tone: 'teal' },
      { label: '测绘文件', value: String(overview.fileCount), meta: '全平台已上传文件', tone: 'blue' },
      { label: '运行中任务', value: String(overview.runningTaskCount), meta: '待审核 / 待分发', tone: 'cyan' },
      { label: '待处理告警', value: String(overview.alertCount), meta: '审计拒绝与错误', tone: 'amber' },
    ]
  } catch {
    // 请求失败时保留占位
  }
})
</script>

<style scoped>
.dash {
  display: grid;
  gap: 18px;
  color: #16324a;
}

.hero,
.glass,
.stat-card {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(56, 132, 176, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(247, 252, 255, 0.88));
  box-shadow:
    0 18px 40px rgba(20, 72, 110, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.hero {
  display: grid;
  grid-template-columns: 1.4fr 0.7fr;
  gap: 20px;
  padding: 22px 24px;
  border-radius: 18px;
  background:
    radial-gradient(500px 180px at 88% 20%, rgba(43, 125, 233, 0.16), transparent 60%),
    radial-gradient(420px 160px at 8% 0%, rgba(15, 157, 142, 0.18), transparent 55%),
    linear-gradient(135deg, #ffffff 0%, #f3fbff 52%, #eef8f6 100%);
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(20, 90, 130, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(20, 90, 130, 0.045) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(90deg, transparent, #000 18%, #000 82%, transparent);
  pointer-events: none;
}

.eyebrow {
  margin: 0;
  color: #0f9d8e;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.hero h2 {
  margin: 8px 0 0;
  font-size: 30px;
  letter-spacing: 0.02em;
}

.lead {
  margin: 10px 0 0;
  max-width: 560px;
  color: #4d6d82;
  line-height: 1.6;
}

.pipeline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}

.pipeline span {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 157, 142, 0.25);
  background: rgba(15, 157, 142, 0.08);
  color: #0b6e64;
  font-size: 12px;
  font-weight: 600;
}

.pipeline i {
  width: 18px;
  height: 1px;
  background: linear-gradient(90deg, #0f9d8e, #2b7de9);
}

.hero-side {
  display: grid;
  justify-items: end;
  align-content: center;
  gap: 12px;
  z-index: 1;
}

.scan-orb {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  border: 1px solid rgba(43, 125, 233, 0.35);
  background:
    radial-gradient(circle at 35% 30%, #fff, transparent 28%),
    conic-gradient(from 90deg, rgba(15, 157, 142, 0.05), rgba(43, 125, 233, 0.55), rgba(15, 157, 142, 0.05));
  box-shadow: 0 0 24px rgba(43, 125, 233, 0.28);
  animation: spin 8s linear infinite;
}

.import-btn {
  display: inline-flex;
  align-items: center;
  border-radius: 12px;
  padding: 11px 16px;
  background: linear-gradient(135deg, #0f9d8e, #2b7de9);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 10px 24px rgba(43, 125, 233, 0.28);
}

.hint-all {
  margin: 0;
  max-width: 220px;
  text-align: right;
  color: #6b8798;
  font-size: 12px;
  line-height: 1.5;
}

.stats,
.charts,
.boards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.stats {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.stat-card,
.glass {
  border-radius: 16px;
  padding: 16px 18px;
}

.stat-card {
  min-height: 118px;
}

.stat-card[data-tone='teal'] { --glow: #0f9d8e; }
.stat-card[data-tone='blue'] { --glow: #2b7de9; }
.stat-card[data-tone='cyan'] { --glow: #1aa6c4; }
.stat-card[data-tone='amber'] { --glow: #d97706; }

.stat-card::after {
  content: '';
  position: absolute;
  right: -20px;
  top: -24px;
  width: 90px;
  height: 90px;
  border-radius: 50%;
}

.stat-card[data-tone='teal']::after { background: radial-gradient(circle, rgba(15, 157, 142, 0.28), transparent 70%); }
.stat-card[data-tone='blue']::after { background: radial-gradient(circle, rgba(43, 125, 233, 0.28), transparent 70%); }
.stat-card[data-tone='cyan']::after { background: radial-gradient(circle, rgba(26, 166, 196, 0.28), transparent 70%); }
.stat-card[data-tone='amber']::after { background: radial-gradient(circle, rgba(217, 119, 6, 0.28), transparent 70%); }

.stat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  color: #5f7e93;
  font-size: 13px;
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--glow);
  box-shadow: 0 0 0 0 rgba(15, 157, 142, 0.45);
  animation: ping 1.8s ease-out infinite;
}

.value {
  margin-top: 12px;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #123047;
}

.meta {
  margin-top: 6px;
  color: #7a93a6;
  font-size: 12px;
}

.board {
  min-height: 360px;
  display: flex;
  flex-direction: column;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #5f8aa3;
}

.panel-head h3 {
  margin: 4px 0 0;
  font-size: 16px;
}

.panel-head a {
  color: #0f9d8e;
  font-size: 13px;
  font-weight: 600;
}

.empty {
  color: #7a93a6;
  padding: 36px 0;
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
  border-bottom: 1px solid rgba(20, 90, 130, 0.08);
  font-size: 13px;
}

th {
  color: #6b8798;
  font-size: 12px;
}

.name {
  font-weight: 700;
}

.sub {
  margin-top: 2px;
  color: #7a93a6;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.bar {
  width: 72px;
  height: 6px;
  border-radius: 999px;
  background: #e7eef3;
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #0f9d8e, #2b7de9);
}

.audit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.audit-list li {
  display: grid;
  grid-template-columns: 92px 1fr auto;
  gap: 10px;
  align-items: start;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(20, 90, 130, 0.08);
}

.time {
  color: #6b8798;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.audit-list p {
  margin: 4px 0 0;
  color: #6b8798;
  font-size: 12px;
  line-height: 1.45;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #eef3f7;
}

.tag[data-s='approved'],
.tag[data-s='completed'],
.tag[data-r='success'] {
  color: #0f7a4a;
  background: rgba(15, 157, 142, 0.12);
}

.tag[data-s='running'],
.tag[data-s='queued'],
.tag[data-s='pending'] {
  color: #1d5ea8;
  background: rgba(43, 125, 233, 0.12);
}

.tag[data-s='waiting_review'],
.tag[data-s='distributing'],
.tag[data-r='denied'] {
  color: #a16207;
  background: rgba(217, 119, 6, 0.12);
}

.tag[data-s='failed'],
.tag[data-s='rejected'],
.tag[data-r='error'] {
  color: #b42318;
  background: rgba(231, 111, 81, 0.12);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes ping {
  70% { box-shadow: 0 0 0 8px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}

@media (max-width: 1100px) {
  .stats,
  .hero {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 800px) {
  .stats,
  .charts,
  .boards,
  .hero,
  .audit-list li {
    grid-template-columns: 1fr;
  }

  .hero-side {
    justify-items: start;
  }

  .hint-all {
    text-align: left;
  }
}
</style>
