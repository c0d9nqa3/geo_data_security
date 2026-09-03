<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="statusFilter">
        <option value="">全部状态</option>
        <option value="queued">排队中</option>
        <option value="running">执行中</option>
        <option value="waiting_review">待审核</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
        <option value="failed">失败</option>
      </select>
      <button type="button" class="primary" @click="showCreate = true">提交任务</button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else class="cards">
      <article v-for="t in filtered" :key="t.id" class="card">
        <div class="card-top">
          <div>
            <div class="id">{{ t.id }}</div>
            <h3>{{ t.type }}</h3>
          </div>
          <span class="tag" :data-s="t.status">{{ statusText(t.status) }}</span>
        </div>
        <dl>
          <div><dt>项目</dt><dd>{{ t.projectName }}</dd></div>
          <div><dt>文件</dt><dd>{{ t.fileName }}</dd></div>
          <div><dt>创建人</dt><dd>{{ t.createdBy }}</dd></div>
          <div><dt>更新</dt><dd>{{ t.updatedAt }}</dd></div>
        </dl>
        <div class="progress">
          <div class="bar"><i :style="{ width: `${t.progress}%` }" /></div>
          <span>{{ t.progress }}%</span>
        </div>
      </article>
    </div>

    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <form class="modal" @submit.prevent="onCreate">
        <h3>提交处理任务</h3>
        <label>
          关联文件
          <select v-model="form.fileId" required>
            <option disabled value="">请选择</option>
            <option v-for="f in files" :key="f.id" :value="f.id">
              {{ f.name }}（{{ f.projectName }}）
            </option>
          </select>
        </label>
        <label>
          任务类型
          <select v-model="form.type">
            <option>GeoTIFF 水印</option>
            <option>矢量水印</option>
            <option>DLG 水印</option>
            <option>OSGB 水印</option>
            <option>脱敏 / 精度处理</option>
          </select>
        </label>
        <p v-if="errorMsg" class="tip" style="color: var(--danger)">{{ errorMsg }}</p>
        <p class="tip">提交后自动进入流转待办，管理员审核通过并分发授权后才会交给服务器2执行。</p>
        <div class="actions">
          <button type="button" class="ghost" @click="showCreate = false">取消</button>
          <button type="submit" class="primary" :disabled="submitting">
            {{ submitting ? '提交中…' : '提交' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchFiles } from '@/modules/ingest/api'
import { createTask, fetchTasks } from '@/modules/task/api'
import type { DataFile, TaskItem, TaskStatus } from '@/types'

const loading = ref(true)
const tasks = ref<TaskItem[]>([])
const files = ref<DataFile[]>([])
const statusFilter = ref('')
const showCreate = ref(false)
const submitting = ref(false)
const errorMsg = ref('')
const form = reactive({ fileId: '', type: 'GeoTIFF 水印' })

const filtered = computed(() =>
  statusFilter.value
    ? tasks.value.filter((t) => t.status === statusFilter.value)
    : tasks.value,
)

function statusText(s: TaskStatus) {
  return (
    {
      queued: '排队中',
      running: '执行中',
      waiting_review: '待审核',
      approved: '已通过',
      rejected: '已驳回',
      failed: '失败',
    } as const
  )[s]
}

onMounted(async () => {
  ;[tasks.value, files.value] = await Promise.all([fetchTasks(), fetchFiles()])
  loading.value = false
})

async function onCreate() {
  errorMsg.value = ''
  submitting.value = true
  try {
    const created = await createTask({ fileId: form.fileId, type: form.type })
    tasks.value = [created, ...tasks.value]
    form.fileId = ''
    showCreate.value = false
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '提交失败'
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

select {
  min-width: 180px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--text);
  padding: 11px 12px;
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

.empty {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: rgba(28, 37, 48, 0.88);
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

.cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: rgba(28, 37, 48, 0.88);
  padding: 16px 18px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.id {
  color: var(--text-muted);
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

h3 {
  margin: 4px 0 0;
  font-size: 17px;
}

dl {
  margin: 14px 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 14px;
}

dl > div {
  display: grid;
  gap: 2px;
}

dt {
  color: var(--text-muted);
  font-size: 12px;
}

dd {
  margin: 0;
  font-size: 13px;
}

.progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--bg);
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #4ea8de);
}

.progress span {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 36px;
}

.tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--bg-hover);
}

.tag[data-s='running'] {
  color: var(--info);
  background: rgba(78, 168, 222, 0.15);
}

.tag[data-s='waiting_review'] {
  color: var(--warn);
  background: rgba(233, 196, 106, 0.15);
}

.tag[data-s='approved'] {
  color: var(--ok);
  background: rgba(82, 183, 136, 0.15);
}

.tag[data-s='failed'],
.tag[data-s='rejected'] {
  color: var(--danger);
  background: rgba(231, 111, 81, 0.15);
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
  margin: 0;
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
}

@media (max-width: 900px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
