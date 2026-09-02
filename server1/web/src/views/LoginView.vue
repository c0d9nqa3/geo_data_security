<template>
  <div class="login-page">
    <section class="panel">
      <div class="panel-copy">
        <p class="eyebrow">测绘地理信息 · 数据安全</p>
        <h1>服务器1 接入控制台</h1>
        <p class="lead">
          在内网终端完成登录、上传、权限校验、任务提交与状态查询。处理与只读结果由服务器2承担。
        </p>
        <ul>
          <li>登录与项目权限</li>
          <li>文件上传与校验</li>
          <li>任务调度与审计</li>
        </ul>
      </div>

      <form class="form" @submit.prevent="onSubmit">
        <h2>登录</h2>
        <label>
          用户名
          <input v-model="username" autocomplete="username" placeholder="admin / 任意操作员" />
        </label>
        <label>
          密码
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="任意非空密码（开发 mock）"
          />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '进入平台' }}
        </button>
        <p class="hint">开发期使用 mock 鉴权；后端 auth 模块就绪后走 /api/auth/login。</p>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '@/api/client'

const router = useRouter()
const route = useRoute()

const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  loading.value = true
  error.value = ''
  try {
    await login(username.value.trim(), password.value)
    const redirect = (route.query.redirect as string) || '/dashboard'
    await router.replace(redirect)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
}

.panel {
  width: min(960px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 0;
  border: 1px solid var(--border);
  border-radius: 18px;
  overflow: hidden;
  background: rgba(23, 30, 38, 0.92);
  box-shadow: var(--shadow);
}

.panel-copy {
  padding: 40px 36px;
  background:
    linear-gradient(160deg, rgba(42, 157, 143, 0.22), transparent 45%),
    linear-gradient(20deg, rgba(78, 168, 222, 0.12), transparent 40%),
    var(--bg-elevated);
}

.eyebrow {
  margin: 0 0 12px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel-copy h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.2;
}

.lead {
  margin: 16px 0 24px;
  color: var(--text-muted);
  line-height: 1.65;
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

li {
  position: relative;
  padding-left: 18px;
  color: var(--text);
}

li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 40px 32px;
}

.form h2 {
  margin: 0 0 8px;
  font-size: 22px;
}

label {
  display: grid;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  color: var(--text);
  padding: 12px 14px;
  outline: none;
}

input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

button[type='submit'] {
  margin-top: 8px;
  border: none;
  border-radius: 10px;
  padding: 12px 16px;
  background: linear-gradient(135deg, var(--accent), #1f7a72);
  color: #fff;
  font-weight: 600;
  transition: transform 0.15s ease, filter 0.15s ease;
}

button[type='submit']:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: translateY(-1px);
}

button[type='submit']:disabled {
  opacity: 0.7;
  cursor: wait;
}

.error {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}

.hint {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 800px) {
  .panel {
    grid-template-columns: 1fr;
  }
}
</style>
