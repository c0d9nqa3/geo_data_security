<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="actionFilter">
        <option value="">全部动作</option>
        <option value="login">登录</option>
        <option value="upload">上传</option>
        <option value="create_project">创建项目</option>
        <option value="submit_task">提交任务</option>
        <option value="approve">审批</option>
        <option value="reject">驳回</option>
        <option value="apply_circulation">流转申请</option>
        <option value="distribute">分发授权</option>
        <option value="delete_circulation">删除流转单</option>
        <option value="download_result">结果下载</option>
        <option value="query_trace">追溯查询</option>
      </select>
      <select v-model="resultFilter">
        <option value="">全部结果</option>
        <option value="success">成功</option>
        <option value="denied">拒绝</option>
        <option value="error">错误</option>
      </select>
    </div>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>操作人</th>
            <th>动作</th>
            <th>项目</th>
            <th>详情</th>
            <th>结果</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in events" :key="e.id">
            <td>{{ e.time }}</td>
            <td>{{ e.actor }}</td>
            <td>{{ actionText(e.action) }}</td>
            <td>{{ e.projectId || '—' }}</td>
            <td>{{ e.detail }}</td>
            <td><span class="tag" :data-r="e.result">{{ resultText(e.result) }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchAudits } from '@/modules/audit/api'
import type { AuditAction, AuditEvent } from '@/types'

const loading = ref(true)
const events = ref<AuditEvent[]>([])
const actionFilter = ref('')
const resultFilter = ref('')

function actionText(a: AuditAction) {
  return (
    {
      login: '登录',
      upload: '上传',
      create_project: '创建项目',
      submit_task: '提交任务',
      approve: '审批',
      reject: '驳回',
      apply_circulation: '流转申请',
      distribute: '分发授权',
      delete_circulation: '删除流转单',
      download_result: '结果下载',
      query_trace: '追溯查询',
    } as const
  )[a]
}

function resultText(r: AuditEvent['result']) {
  return ({ success: '成功', denied: '拒绝', error: '错误' } as const)[r]
}

async function load() {
  loading.value = true
  try {
    events.value = await fetchAudits(actionFilter.value || undefined, resultFilter.value || undefined)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch([actionFilter, resultFilter], load)
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

select {
  min-width: 160px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 11px 12px;
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
  vertical-align: top;
}

th {
  font-size: 12px;
  color: var(--text-muted);
}

tr:last-child td {
  border-bottom: none;
}

.tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.tag[data-r='success'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.15);
}

.tag[data-r='denied'] {
  color: var(--warn);
  background: rgba(233, 196, 106, 0.15);
}

.tag[data-r='error'] {
  color: var(--danger);
  background: rgba(231, 111, 81, 0.15);
}
</style>
