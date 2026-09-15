<template>
  <section class="volume" :class="{ danger: hasAlert }">
    <div class="scan" aria-hidden="true" />
    <div class="head">
      <div>
        <p class="kicker">CAPACITY RADAR · 7-CLASS VOLUME</p>
        <h3>数据体量分析</h3>
        <p class="sub">按年度 / 月份统计七类上传数据；单类或总量达到 1 万条、或存储达到 10 GB 时深红色预警。</p>
      </div>
      <div class="controls">
        <div class="pills">
          <button type="button" :class="{ on: granularity === 'month' }" @click="setGranularity('month')">按月</button>
          <button type="button" :class="{ on: granularity === 'year' }" @click="setGranularity('year')">按年</button>
        </div>
        <select v-if="granularity === 'month'" v-model.number="year" @change="reload">
          <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
        </select>
        <div class="pills">
          <button type="button" :class="{ on: metric === 'count' }" @click="metric = 'count'">条数</button>
          <button type="button" :class="{ on: metric === 'bytes' }" @click="metric = 'bytes'">容量</button>
        </div>
      </div>
    </div>

    <div v-if="hasAlert" class="alert-banner">
      <strong>容量预警</strong>
      <span>{{ alertText }}</span>
    </div>

    <div class="gauges">
      <article class="gauge" :class="{ alert: overview?.countAlert }">
        <div class="gauge-top">
          <span>累计条数</span>
          <b>{{ formatCount(overview?.totalCount ?? 0) }}</b>
        </div>
        <div class="track"><i :style="{ width: countPct + '%' }" /></div>
        <p>阈值 {{ formatCount(overview?.countThreshold ?? 10000) }} 条 · {{ countPct.toFixed(1) }}%</p>
      </article>
      <article class="gauge" :class="{ alert: overview?.bytesAlert }">
        <div class="gauge-top">
          <span>累计存储</span>
          <b>{{ formatBytes(overview?.totalBytes ?? 0) }}</b>
        </div>
        <div class="track"><i :style="{ width: bytesPct + '%' }" /></div>
        <p>阈值 {{ formatBytes(overview?.bytesThreshold ?? 10 * 1024 * 1024 * 1024) }} · {{ bytesPct.toFixed(1) }}%</p>
      </article>
    </div>
    <p v-if="(overview?.unclassifiedCount ?? 0) > 0" class="note">
      另有 {{ formatCount(overview?.unclassifiedCount ?? 0) }} 条历史“其他”类数据（{{ formatBytes(overview?.unclassifiedBytes ?? 0) }}）未归入七类曲线，确认分类后可一并统计。
    </p>

    <div class="kind-grid">
      <article
        v-for="kind in overview?.kinds || []"
        :key="kind.code"
        class="kind-card"
        :class="{ alert: kind.countAlert || kind.bytesAlert }"
      >
        <div class="kind-top">
          <span class="dot" :style="{ background: kind.color }" />
          <div>
            <strong>{{ kind.title }}</strong>
            <small v-if="kind.label && kind.label !== kind.title">{{ kind.label }}</small>
          </div>
          <em v-if="kind.countAlert || kind.bytesAlert">预警</em>
        </div>
        <div class="kind-nums">
          <span>{{ formatCount(kind.totalCount) }} 条</span>
          <span>{{ formatBytes(kind.totalBytes) }}</span>
        </div>
        <div class="mini-track">
          <i :style="{ width: pct(kind.totalCount, overview?.countThreshold ?? 10000) + '%', background: kind.color }" />
        </div>
      </article>
    </div>

    <div v-if="loading" class="empty">加载体量曲线…</div>
    <template v-else>
      <p v-if="(overview?.totalCount ?? 0) === 0" class="empty">暂无上传记录。上传后将按七类计入年/月曲线；触及 1 万条或 10 GB 时深红色预警。</p>
      <VolumeTrendChart
        :title="chartTitle"
        :unit="metric === 'count' ? '条' : 'GB'"
        :threshold="chartThreshold"
        :threshold-label="chartThresholdLabel"
        :series="chartSeries"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchDataVolume, type DataVolumeOverview } from '@/modules/dashboard/api'
import VolumeTrendChart from '@/shared/VolumeTrendChart.vue'

const loading = ref(true)
const granularity = ref<'month' | 'year'>('month')
const year = ref(new Date().getFullYear())
const years = ref<number[]>([year.value])
const metric = ref<'count' | 'bytes'>('count')
const overview = ref<DataVolumeOverview | null>(null)

const hasAlert = computed(() => {
  const data = overview.value
  if (!data) return false
  return data.countAlert || data.bytesAlert || data.kinds.some((k) => k.countAlert || k.bytesAlert)
})

const alertText = computed(() => {
  const data = overview.value
  if (!data) return ''
  const hits = data.kinds.filter((k) => k.countAlert || k.bytesAlert).map((k) => k.title)
  const parts: string[] = []
  if (data.countAlert) parts.push(`总量已达 ${formatCount(data.totalCount)} 条`)
  if (data.bytesAlert) parts.push(`总存储已达 ${formatBytes(data.totalBytes)}`)
  if (hits.length) parts.push(`${hits.join('、')} 触及阈值`)
  return parts.join('；') || '已触及容量阈值'
})

const countPct = computed(() => pct(overview.value?.totalCount ?? 0, overview.value?.countThreshold ?? 10000))
const bytesPct = computed(() => pct(overview.value?.totalBytes ?? 0, overview.value?.bytesThreshold ?? 10 * 1024 * 1024 * 1024))

const chartTitle = computed(() =>
  metric.value === 'count'
    ? granularity.value === 'year' ? '七类数据年条数' : `${year.value} 年七类数据月条数`
    : granularity.value === 'year' ? '七类数据年容量' : `${year.value} 年七类数据月容量`
)

const chartThreshold = computed(() => {
  if (metric.value === 'count') return overview.value?.countThreshold ?? 10000
  return gb(overview.value?.bytesThreshold ?? 10 * 1024 * 1024 * 1024)
})

const chartThresholdLabel = computed(() =>
  metric.value === 'count' ? '预警 10,000 条' : '预警 10 GB'
)

const chartSeries = computed(() =>
  (overview.value?.kinds ?? []).map((kind) => ({
    code: kind.code,
    label: kind.title,
    color: kind.color,
    alert: kind.countAlert || kind.bytesAlert,
    points: kind.points.map((p) => ({
      period: p.period,
      value: metric.value === 'count' ? p.count : gb(p.bytes),
    })),
  }))
)

function gb(bytes: number) {
  return Math.round((bytes / (1024 * 1024 * 1024)) * 1000) / 1000
}

function pct(value: number, max: number) {
  if (max <= 0) return 0
  return Math.max(0, Math.min(100, (value / max) * 100))
}

function formatCount(n: number) {
  return n.toLocaleString('zh-CN')
}

function formatBytes(bytes: number) {
  const g = bytes / (1024 * 1024 * 1024)
  if (g >= 1) return `${g.toFixed(2)} GB`
  const m = bytes / (1024 * 1024)
  if (m >= 1) return `${m.toFixed(1)} MB`
  const k = bytes / 1024
  if (k >= 1) return `${k.toFixed(1)} KB`
  return `${bytes} B`
}

function setGranularity(next: 'month' | 'year') {
  granularity.value = next
  reload()
}

async function reload() {
  loading.value = true
  try {
    const data = await fetchDataVolume({
      granularity: granularity.value,
      year: granularity.value === 'month' ? year.value : undefined,
    })
    overview.value = data
    years.value = data.years?.length ? data.years : [data.year]
    year.value = data.year
  } catch {
    overview.value = null
  } finally {
    loading.value = false
  }
}

onMounted(reload)
</script>

<style scoped>
.volume {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 18px 18px 16px;
  color: #d7f4ff;
  border: 1px solid rgba(80, 200, 220, 0.28);
  background:
    radial-gradient(720px 220px at 8% -10%, rgba(34, 211, 238, 0.16), transparent 58%),
    radial-gradient(520px 200px at 96% 110%, rgba(59, 130, 246, 0.16), transparent 55%),
    linear-gradient(165deg, #07141d 0%, #0b1d29 52%, #08141c 100%);
  box-shadow: 0 22px 48px rgba(6, 24, 36, 0.22), inset 0 1px 0 rgba(180, 240, 255, 0.08);
}

.volume.danger {
  border-color: #8b0000;
  box-shadow:
    0 0 0 1px rgba(139, 0, 0, 0.55),
    0 22px 48px rgba(80, 0, 0, 0.18),
    inset 0 1px 0 rgba(180, 240, 255, 0.08);
}

.scan {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(125, 211, 232, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(125, 211, 232, 0.045) 1px, transparent 1px);
  background-size: 24px 24px;
  mask-image: linear-gradient(180deg, #000 0%, transparent 88%);
  pointer-events: none;
  animation: drift 18s linear infinite;
}

.head,
.controls,
.gauges,
.kind-grid {
  position: relative;
  z-index: 1;
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.kicker {
  margin: 0;
  color: #67e8f9;
  font-size: 11px;
  letter-spacing: 0.16em;
  font-weight: 700;
}

.head h3 {
  margin: 6px 0 0;
  font-size: 20px;
  color: #f2fdff;
}

.sub {
  margin: 8px 0 0;
  max-width: 640px;
  color: #93c5d4;
  font-size: 12px;
  line-height: 1.55;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.pills {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  background: rgba(4, 18, 28, 0.7);
  border: 1px solid rgba(103, 232, 249, 0.2);
}

.pills button,
select {
  border: 0;
  background: transparent;
  color: #c4e8f3;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.pills button.on {
  background: linear-gradient(135deg, #155e75, #0e7490);
  color: #fff;
}

select {
  border: 1px solid rgba(103, 232, 249, 0.2);
  background: rgba(4, 18, 28, 0.7);
}

.alert-banner {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 12px;
  background: linear-gradient(90deg, #4a0000, #8b0000 55%, #5c0000);
  border: 1px solid #7f1d1d;
  color: #fecaca;
  box-shadow: 0 0 24px rgba(139, 0, 0, 0.35);
}

.alert-banner strong {
  padding: 2px 8px;
  border-radius: 999px;
  background: #7f1d1d;
  color: #fff;
  font-size: 12px;
}

.gauges {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
}

.gauge,
.kind-card {
  border-radius: 12px;
  padding: 12px;
  background: rgba(5, 18, 28, 0.55);
  border: 1px solid rgba(125, 211, 232, 0.16);
}

.gauge.alert,
.kind-card.alert {
  border-color: #8b0000;
  background: linear-gradient(180deg, rgba(139, 0, 0, 0.28), rgba(8, 16, 22, 0.7));
}

.gauge-top,
.kind-top,
.kind-nums {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.gauge-top span,
.kind-card small {
  color: #8fb8c8;
  font-size: 12px;
}

.gauge-top b {
  font-size: 22px;
  color: #f0fdff;
}

.gauge p {
  margin: 8px 0 0;
  color: #7aa3b3;
  font-size: 12px;
}

.track,
.mini-track {
  margin-top: 10px;
  height: 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.track i,
.mini-track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #22d3ee, #3b82f6);
}

.gauge.alert .track i {
  background: linear-gradient(90deg, #7f1d1d, #8b0000);
}

.kind-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0 8px;
}

.kind-top {
  align-items: flex-start;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-top: 4px;
  box-shadow: 0 0 10px currentColor;
  flex: none;
}

.kind-card strong {
  display: block;
  font-size: 12px;
  line-height: 1.35;
  color: #f2fdff;
}

.kind-card em {
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  color: #fecaca;
  background: #8b0000;
  border-radius: 999px;
  padding: 1px 6px;
}

.kind-nums {
  margin-top: 10px;
  color: #c7eaf4;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.empty {
  color: #8fb8c8;
  text-align: center;
  padding: 28px 0;
}

.note {
  position: relative;
  z-index: 1;
  margin: 10px 0 4px;
  color: #93c5d4;
  font-size: 12px;
}

@keyframes drift {
  to { background-position: 24px 24px; }
}

@media (max-width: 1200px) {
  .kind-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 800px) {
  .head,
  .gauges,
  .kind-grid {
    grid-template-columns: 1fr;
  }

  .head {
    display: grid;
  }
}
</style>
