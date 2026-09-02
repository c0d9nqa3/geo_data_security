<template>
  <div class="page">
    <section class="stats">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <div class="label">{{ card.label }}</div>
        <div class="value">{{ card.value }}</div>
        <div class="meta">{{ card.meta }}</div>
      </article>
    </section>

    <section class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <h2>成员1职责覆盖</h2>
          <span>本前端对应能力</span>
        </div>
        <ul class="checklist">
          <li v-for="item in duties" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>数据流提示</h2>
          <span>与冻结架构一致</span>
        </div>
        <ol class="flow">
          <li>终端 Web → 服务器1：登录 / 上传 / 任务 / 状态</li>
          <li>服务器1 → 服务器2：内部转交与任务编排</li>
          <li>终端 Web → 服务器2：仅审核通过结果只读获取</li>
        </ol>
        <p class="note">
          当前为前后端分离：页面在 <code>server1/web</code>，接口由
          <code>gateway/auth/project/…</code> 提供；开发期使用 mock 数据。
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchFiles, fetchProjects, fetchTasks } from '@/api/client'

const cards = ref([
  { label: '项目', value: '—', meta: '项目管理' },
  { label: '文件', value: '—', meta: '上传与校验索引' },
  { label: '任务', value: '—', meta: '调度与进度' },
  { label: '待审核', value: '—', meta: '流转审批' },
])

const duties = [
  'Web 界面（本目录）',
  '后端 API（gateway 等模块，待接）',
  '登录权限',
  '项目管理 / 文件管理 / 任务管理',
  '服务间通信与配置（后续）',
  '部署脚本（deploy/server1）',
]

onMounted(async () => {
  const [projects, files, tasks] = await Promise.all([
    fetchProjects(),
    fetchFiles(),
    fetchTasks(),
  ])
  cards.value = [
    { label: '项目', value: String(projects.length), meta: '项目管理' },
    { label: '文件', value: String(files.length), meta: '上传与校验索引' },
    { label: '任务', value: String(tasks.length), meta: '调度与进度' },
    {
      label: '待审核',
      value: String(tasks.filter((t) => t.status === 'waiting_review').length),
      meta: '流转审批',
    },
  ]
})
</script>

<style scoped>
.page {
  display: grid;
  gap: 20px;
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
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: rgba(42, 157, 143, 0.55);
}

.label {
  color: var(--text-muted);
  font-size: 13px;
}

.value {
  margin-top: 10px;
  font-size: 32px;
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

.panel {
  padding: 18px 20px 20px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-head h2 {
  margin: 0;
  font-size: 16px;
}

.panel-head span {
  color: var(--text-muted);
  font-size: 12px;
}

.checklist,
.flow {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
  color: var(--text);
  line-height: 1.5;
}

.note {
  margin: 16px 0 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--accent-soft);
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
}

code {
  color: var(--accent-hover);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}

@media (max-width: 980px) {
  .stats,
  .grid-2 {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .stats,
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
