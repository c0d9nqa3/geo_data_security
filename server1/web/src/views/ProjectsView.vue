<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索项目名称 / 编号" />
      <button type="button" class="primary" @click="showCreate = true">新建项目</button>
    </div>
    <p class="hint">{{ reviewer ? '管理员可查看全部项目。' : '你只能看到自己新建的项目，提交后可在流转控制跟踪审核状态。' }}</p>

    <div class="table-wrap">
      <div v-if="loading" class="empty-inline">加载中…</div>
      <table v-else>
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
          <tr v-for="p in projects" :key="p.id">
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
      <div v-if="!loading && !projects.length" class="empty-inline">暂无项目</div>
      <PagerBar v-model:page="page" v-model:page-size="pageSize" :total="total" :total-pages="totalPages" :loading="loading" />
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
        <p class="tip">提交后自动进入流转待办和任务管理流程图。管理员审核通过后，提交人可到流转控制向服务器2分发，项目才会生效。未审核前可在任务管理撤回。</p>
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
import { onMounted, reactive, ref, watch } from 'vue'
import { createProject, fetchProjects } from '@/modules/project/api'
import { canReview } from '@/shared/access'
import PagerBar from '@/shared/PagerBar.vue'
import type { Project } from '@/types'

const reviewer = canReview()

const loading = ref(true)
const projects = ref<Project[]>([])
const total = ref(0)
const totalPages = ref(1)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const showCreate = ref(false)
const submitting = ref(false)
const form = reactive({ name: '', code: '', description: '' })
const errorMsg = ref('')

function statusText(s: Project['status']) {
  return ({ active: '进行中', archived: '已归档', draft: '草稿' } as const)[s]
}

async function reload() {
  loading.value = true
  try {
    const data = await fetchProjects({
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    projects.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
    page.value = data.page
    pageSize.value = data.pageSize
  } catch {
    projects.value = []
    total.value = 0
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

onMounted(reload)
watch(keyword, () => {
  page.value = 1
})
watch(pageSize, () => {
  page.value = 1
})
watch([page, pageSize, keyword], reload)

async function onCreate() {
  errorMsg.value = ''
  submitting.value = true
  try {
    await createProject({
      name: form.name,
      code: form.code,
      description: form.description || '新建项目',
    })
    form.name = ''
    form.code = ''
    form.description = ''
    showCreate.value = false
    page.value = 1
    await reload()
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

.hint {
  margin: 0;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: rgba(78, 168, 222, 0.08);
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
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
  background: var(--bg-card);
  box-shadow: var(--shadow);
}

.empty {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

.empty-inline {
  padding: 28px 14px;
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
  background: rgba(15, 157, 142, 0.06);
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
