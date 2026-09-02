<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true" />
        <div>
          <div class="brand-title">数据安全平台</div>
          <div class="brand-sub">服务器1 · 接入控制面</div>
        </div>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="active"
        >
          <span class="nav-dot" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <div class="user-chip">
          <strong>{{ user?.displayName ?? '未登录' }}</strong>
          <span>{{ roleLabel }}</span>
        </div>
        <button type="button" class="ghost-btn" @click="onLogout">退出</button>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div>
          <h1>{{ title }}</h1>
          <p>终端通过本界面访问服务器1业务能力；结果只读接口由服务器2提供。</p>
        </div>
        <div class="env-pill">测试环境 · Win10</div>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter, RouterLink, RouterView } from 'vue-router'
import { getStoredUser, logout } from '@/api/client'

const route = useRoute()
const router = useRouter()
const user = getStoredUser()

const nav = [
  { to: '/dashboard', label: '工作台' },
  { to: '/projects', label: '项目管理' },
  { to: '/files', label: '文件管理' },
  { to: '/tasks', label: '任务管理' },
  { to: '/audit', label: '审计追溯' },
]

const title = computed(() => (route.meta.title as string) || '工作台')

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    admin: '管理员',
    operator: '操作员',
    auditor: '审计员',
    viewer: '只读',
  }
  return user ? map[user.role] ?? user.role : ''
})

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 100vh;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 24px 18px;
  border-right: 1px solid var(--border);
  background: rgba(15, 20, 25, 0.88);
  backdrop-filter: blur(10px);
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 4px 8px;
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background:
    linear-gradient(145deg, var(--accent), #1d6f78 55%, #4ea8de);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
}

.brand-title {
  font-weight: 700;
  letter-spacing: 0.02em;
}

.brand-sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-muted);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 8px;
  color: var(--text-muted);
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text);
  transform: translateX(2px);
}

.nav-item.active {
  background: var(--accent-soft);
  color: var(--text);
}

.nav-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.45;
}

.nav-item.active .nav-dot {
  background: var(--accent);
  opacity: 1;
}

.sidebar-foot {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.user-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg-panel);
}

.user-chip span {
  font-size: 12px;
  color: var(--text-muted);
}

.ghost-btn {
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-muted);
  border-radius: 8px;
  padding: 8px 10px;
}

.ghost-btn:hover {
  color: var(--text);
  border-color: var(--accent);
}

.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 28px 32px 12px;
}

.topbar h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.topbar p {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 14px;
  max-width: 560px;
  line-height: 1.5;
}

.env-pill {
  flex-shrink: 0;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-panel);
  color: var(--text-muted);
  font-size: 12px;
}

.content {
  padding: 12px 32px 40px;
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid var(--border);
  }

  .nav {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .topbar,
  .content {
    padding-left: 18px;
    padding-right: 18px;
  }
}
</style>
