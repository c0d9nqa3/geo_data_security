<template>
  <div class="bell-wrap" ref="root">
    <button
      type="button"
      class="bell-btn"
      :class="{ open: open }"
      :aria-label="unreadCount > 0 ? `未读消息 ${unreadCount} 条` : '消息中心'"
      @click="toggle"
    >
      <svg class="bell-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 3a6.5 6.5 0 0 0-6.5 6.5v2.2l-1.6 3.1A1 1 0 0 0 4.8 16.5h14.4a1 1 0 0 0 .9-1.7l-1.6-3.1V9.5A6.5 6.5 0 0 0 12 3Z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linejoin="round"
        />
        <path d="M9.4 17.4a2.7 2.7 0 0 0 5.2 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
      </svg>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <div v-if="open" class="panel">
      <div class="panel-head">
        <div>
          <strong>消息中心</strong>
          <span>{{ unreadCount > 0 ? `${unreadCount} 条未读` : '暂无未读' }}</span>
        </div>
        <button
          v-if="unreadCount > 0"
          type="button"
          class="link-btn"
          :disabled="busy"
          @click="onReadAll"
        >
          全部已读
        </button>
      </div>
      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="errorMsg" class="empty error">{{ errorMsg }}</div>
      <div v-else-if="!items.length" class="empty">暂无催办消息</div>
      <ul v-else class="list">
        <li v-for="item in items" :key="item.id" :class="{ unread: !item.read }">
          <button type="button" class="item" @click="onOpen(item)">
            <div class="item-top">
              <em>{{ item.title || '待审核催办' }}</em>
              <time>{{ item.createdAt || '—' }}</time>
            </div>
            <p>{{ item.content }}</p>
            <dl>
              <div><dt>提交人</dt><dd>{{ item.senderName || '—' }}</dd></div>
              <div><dt>类型</dt><dd>{{ item.applyTypeLabel || '—' }}</dd></div>
              <div v-if="item.projectName"><dt>项目</dt><dd>{{ item.projectName }}</dd></div>
            </dl>
            <span class="go">{{ item.read ? '查看单据' : '去审核' }}</span>
          </button>
        </li>
      </ul>
      <p v-if="errorMsg && items.length" class="error">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchNoticeUnreadCount,
  fetchNotices,
  markAllNoticesRead,
  markNoticeRead,
} from '@/modules/notice/api'
import type { NoticeItem } from '@/types'

const router = useRouter()
const root = ref<HTMLElement | null>(null)
const open = ref(false)
const loading = ref(false)
const busy = ref(false)
const unreadCount = ref(0)
const items = ref<NoticeItem[]>([])
const errorMsg = ref('')

async function refreshCount() {
  try {
    const data = await fetchNoticeUnreadCount()
    unreadCount.value = data.unreadCount || 0
  } catch {
    // 轮询失败时保持上次数字
  }
}

async function reloadList() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await fetchNotices({ page: 1, pageSize: 20 })
    items.value = data.items
    await refreshCount()
  } catch (e) {
    items.value = []
    errorMsg.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await reloadList()
  }
}

async function onReadAll() {
  busy.value = true
  try {
    const data = await markAllNoticesRead()
    unreadCount.value = data.unreadCount || 0
    items.value = items.value.map((item) => ({ ...item, read: true }))
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function onOpen(item: NoticeItem) {
  try {
    if (!item.read) {
      const updated = await markNoticeRead(item.id)
      items.value = items.value.map((row) => (row.id === updated.id ? updated : row))
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  } catch {
    // 仍允许跳转
  }
  open.value = false
  if (item.circulationId) {
    await router.push({ name: 'circulation', query: { circulationId: item.circulationId } })
  } else {
    await router.push({ name: 'tasks' })
  }
}

function onDocClick(event: MouseEvent) {
  if (!open.value) return
  const target = event.target as Node | null
  if (target && root.value && !root.value.contains(target)) {
    open.value = false
  }
}

let timer = 0
onMounted(() => {
  void refreshCount()
  timer = window.setInterval(() => {
    void refreshCount()
  }, 20_000)
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.bell-wrap {
  position: relative;
}
.bell-btn {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.92);
  color: #1d6f9a;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.bell-btn.open,
.bell-btn:hover {
  border-color: rgba(15, 157, 142, 0.45);
  background: #fff;
  color: #0b6e64;
}
.bell-icon {
  width: 20px;
  height: 20px;
}
.badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e76f51;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  text-align: center;
  box-shadow: 0 0 0 2px #fff;
}
.panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: min(420px, calc(100vw - 36px));
  max-height: min(72vh, 560px);
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(78, 168, 222, 0.22);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(20, 72, 110, 0.16);
  z-index: 40;
  overflow: hidden;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border);
}
.panel-head strong {
  display: block;
  font-size: 15px;
}
.panel-head span {
  margin-top: 2px;
  display: block;
  color: var(--text-muted);
  font-size: 12px;
}
.link-btn {
  border: none;
  background: none;
  color: #1d6f9a;
  font-size: 12px;
  font-weight: 600;
  padding: 0;
}
.link-btn:disabled {
  opacity: 0.45;
}
.empty,
.error {
  margin: 0;
  padding: 28px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
.error {
  color: var(--danger);
  padding-top: 0;
}
.list {
  margin: 0;
  padding: 0;
  list-style: none;
  overflow: auto;
}
.item {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 8px;
}
.unread .item {
  background: rgba(15, 157, 142, 0.06);
}
.item:hover {
  background: rgba(78, 168, 222, 0.08);
}
.item-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: baseline;
}
.item-top em {
  font-style: normal;
  font-weight: 700;
  font-size: 13px;
}
.item-top time {
  color: var(--text-muted);
  font-size: 12px;
  white-space: nowrap;
}
.item p {
  margin: 0;
  color: var(--text);
  font-size: 13px;
  line-height: 1.5;
}
.item dl {
  margin: 0;
  display: grid;
  gap: 4px;
}
.item dl div {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 6px;
  font-size: 12px;
}
dt {
  color: var(--text-muted);
}
dd {
  margin: 0;
}
.go {
  color: #0b6e64;
  font-size: 12px;
  font-weight: 600;
}
</style>
