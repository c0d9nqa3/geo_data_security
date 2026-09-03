<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索项目名称 / 编号" />
      <button type="button" class="primary" @click="showCreate = true">新建项目</button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>项目编号</th>
            <th>名称</th>
            <th>状态</th>
            <th>负责人</th>
            <th>成员</th>
            <th>文件数</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in filtered" :key="p.id">
            <td><code>{{ p.code }}</code></td>
            <td>
              <div class="name">{{ p.name }}</div>
              <div class="desc">{{ p.description }}</div>
            </td>
            <td><span class="tag" :data-s="p.status">{{ statusText(p.status) }}</span></td>
            <td>{{ p.owner }}</td>
            <td>{{ p.memberCount }}</td>
            <td>{{ p.fileCount }}</td>
            <td>{{ p.updatedAt }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <form class="modal" @submit.prevent="onCreate">
        <h3>新建项目</h3>
        <label>
          项目名称
          <input v-model="form.name" required placeholder="例如：城区正射影像库" />
        </label>
        <label>
          项目编号
          <input v-model="form.code" required placeholder="例如：DOM-2026-04" />
        </label>
        <label>
          说明
          <textarea v-model="form.description" rows="3" placeholder="项目用途与数据范围" />
        </label>
        <p v-if="errorMsg" class="tip" style="color: var(--danger)">{{ errorMsg }}</p>
        <p class="tip">提交后自动进入流转待办，管理员审核通过并分发授权后项目才会生效。</p>
        <div class="actions">
          <button type="button" class="ghost" @click="showCreate = false">取消</button>
          <button type="submit" class="primary" :disabled="submitting">
            {{ submitting ? '创建中…' : '创建' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createProject, fetchProjects } from '@/modules/project/api'
import type { Project } from '@/types'

const loading = ref(true)
const projects = ref<Project[]>([])
const keyword = ref('')
const showCreate = ref(false)
const submitting = ref(false)
const form = reactive({ name: '', code: '', description: '' })
const errorMsg = ref('')

const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return projects.value
  return projects.value.filter(
    (p) => p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q),
  )
})

function statusText(s: Project['status']) {
  return ({ active: '进行中', archived: '已归档', draft: '草稿' } as const)[s]
}

onMounted(async () => {
  projects.value = await fetchProjects()
  loading.value = false
})

async function onCreate() {
  errorMsg.value = ''
  submitting.value = true
  try {
    const created = await createProject({
      name: form.name,
      code: form.code,
      description: form.description || '新建项目',
    })
    projects.value = [created, ...projects.value]
    form.name = ''
    form.code = ''
    form.description = ''
    showCreate.value = false
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    submitting.value = false
  }
}
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

.toolbar input,
.modal input,
.modal textarea {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 11px 12px;
  outline: none;
}

.toolbar input:focus,
.modal input:focus,
.modal textarea:focus {
  border-color: var(--accent);
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
  font-weight: 600;
}

tr:last-child td {
  border-bottom: none;
}

.name {
  font-weight: 600;
}

.desc {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--info);
}

.tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--bg-hover);
}

.tag[data-s='active'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.15);
}

.tag[data-s='draft'] {
  color: var(--warn);
  background: rgba(233, 196, 106, 0.15);
}

.tag[data-s='archived'] {
  color: var(--text-muted);
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 50;
}

.modal {
  width: min(460px, 100%);
  display: grid;
  gap: 12px;
  padding: 22px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
}

.modal h3 {
  margin: 0 0 4px;
}

.modal label {
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

.tip {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
</style>
