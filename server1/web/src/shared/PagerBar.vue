<script setup lang="ts">
import { ref, watch } from 'vue'

const page = defineModel<number>('page', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })

const props = defineProps<{
  total: number
  totalPages: number
  loading?: boolean
}>()

const jumpPage = ref(page.value)

watch(page, (value) => {
  jumpPage.value = value
})

function goJump() {
  const target = Number(jumpPage.value)
  if (!Number.isFinite(target)) return
  page.value = Math.min(Math.max(1, Math.trunc(target)), Math.max(props.totalPages, 1))
}
</script>

<template>
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
</template>

<style scoped>
.pager {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: center;
  padding: 12px 14px;
  border-top: 1px solid var(--border);
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
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
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
.btn-page {
  border-radius: 8px;
  padding: 6px 12px;
  border: 1px solid rgba(78, 168, 222, 0.28);
  background: rgba(78, 168, 222, 0.1);
  color: #1d6f9a;
  font-size: 12px;
  font-weight: 600;
}
.btn-page:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
