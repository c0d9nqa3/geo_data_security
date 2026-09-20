<template>
  <div v-if="summary" class="v-panel">
    <p class="caption">校验结果摘要（下方可展开查看原始数据）</p>
    <table class="v-table">
      <tbody>
        <tr v-for="row in rows" :key="row.label">
          <th>{{ row.label }}</th>
          <td>{{ row.value }}</td>
        </tr>
      </tbody>
    </table>
    <details v-if="rawJson" class="raw">
      <summary>展开原始返回数据</summary>
      <pre>{{ rawJson }}</pre>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { buildVerificationSummary, type VerificationSummary } from '@/modules/gds/verificationSummary'

const props = defineProps<{
  data: Record<string, unknown> | null
}>()

const summary = computed<VerificationSummary | null>(() =>
  props.data ? buildVerificationSummary(props.data) : null,
)

const rawJson = computed(() => (props.data ? JSON.stringify(props.data, null, 2) : ''))

function displayBool(v: string) {
  if (v === 'true' || v === 'True') return '是'
  if (v === 'false' || v === 'False') return '否'
  return v
}

function displayStatus(s: string) {
  const map: Record<string, string> = {
    VERIFIED: '已校验通过',
    FAILED: '校验未通过',
    PENDING: '待校验',
  }
  return map[s] ?? s
}

const rows = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: '校验状态', value: displayStatus(s.status) },
    { label: '是否通过', value: displayBool(s.verified) },
    { label: '校验方式', value: s.method },
    { label: '匹配数 / 样本数', value: `${s.matched} / ${s.filesProcessed}` },
    { label: '不可嵌水印数', value: s.notWatermarkable },
    { label: '失败数', value: s.failed },
    { label: '凭证链摘要', value: s.traceHash },
    { label: '区块链锚定', value: displayBool(s.besu) === '是' || s.besu === 'true' ? '已锚定' : s.besu },
  ]
})
</script>

<style scoped>
.v-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.caption {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-muted, var(--muted));
}
.v-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.v-table th {
  text-align: left;
  width: 38%;
  padding: 0.35rem 0.5rem;
  color: var(--text-muted, var(--muted));
  font-weight: 500;
  vertical-align: top;
}
.v-table td {
  padding: 0.35rem 0.5rem;
  word-break: break-all;
}
.raw pre {
  max-height: 240px;
  overflow: auto;
  font-size: 0.72rem;
  padding: 0.5rem;
  background: var(--bg-panel, #0f1419);
  color: #c9d1d9;
  border-radius: 6px;
}
</style>
