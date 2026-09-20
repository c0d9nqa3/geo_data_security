<template>
  <section class="volume" :class="{ danger: hasAlert }">
    <div class="scan" aria-hidden="true" />
    <div class="head">
      <div>
        <p class="kicker">CAPACITY RADAR · 7-CLASS VOLUME</p>
        <h3>数据体量分析</h3>
        <p class="sub">按年度 / 月份统计七类上传数据；单类或总量达到 1 万条、或存储达到 10 GB 时触发容量预警。</p>
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

    <div v-if="hasAlert" class="alert-banner" :data-level="alertLevel">
      <div class="alert-chevron" aria-hidden="true" />
      <div class="alert-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22">
          <path
            fill="currentColor"
            d="M12 2L1 21h22L12 2zm0 4.5L19.1 19H4.9L12 6.5zM11 10v5h2v-5h-2zm0 6v2h2v-2h-2z"
          />
        </svg>
      </div>
      <div class="alert-body">
        <div class="alert-title">
          <strong>容量预警</strong>
          <span class="alert-chip">{{ alertLevelLabel }}</span>
        </div>
        <span class="alert-text">{{ alertText }}</span>
      </div>
      <div class="alert-pct">
        <em>{{ Math.max(countPct, bytesPct).toFixed(0) }}%</em>
        <small>峰值占用</small>
      </div>
      <div class="alert-chevron mirror" aria-hidden="true" />
    </div>

    <div class="gauges">
      <article class="gauge" :class="gaugeClass(countPct, !!overview?.countAlert)">
        <div class="gauge-top">
          <span>累计条数</span>
          <b>{{ formatCount(overview?.totalCount ?? 0) }}</b>
        </div>
        <div class="track">
          <i
            class="fill"
            :class="fillTone(countPct, !!overview?.countAlert)"
            :style="{ width: countPct + '%' }"
          >
            <span class="chevrons" aria-hidden="true"><<<<<<<<<<<<<<<<<<<<</span>
          </i>
          <span class="pct-badge">{{ countPct.toFixed(1) }}%</span>
        </div>
        <p>阈值 {{ formatCount(overview?.countThreshold ?? 10000) }} 条 · 已用 {{ countPct.toFixed(1) }}%</p>
      </article>
      <article class="gauge" :class="gaugeClass(bytesPct, !!overview?.bytesAlert)">
        <div class="gauge-top">
          <span>累计存储</span>
          <b>{{ formatBytes(overview?.totalBytes ?? 0) }}</b>
        </div>
        <div class="track">
          <i
            class="fill"
            :class="fillTone(bytesPct, !!overview?.bytesAlert)"
            :style="{ width: bytesPct + '%' }"
          >
            <span class="chevrons" aria-hidden="true"><<<<<<<<<<<<<<<<<<<<</span>
          </i>
          <span class="pct-badge">{{ bytesPct.toFixed(1) }}%</span>
        </div>
        <p>阈值 {{ formatBytes(overview?.bytesThreshold ?? 10 * 1024 * 1024 * 1024) }} · 已用 {{ bytesPct.toFixed(1) }}%</p>
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
          <em v-if="kind.countAlert || kind.bytesAlert">
            <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
              <path fill="currentColor" d="M12 2L1 21h22L12 2zm1 14h-2v2h2v-2zm0-6h-2v5h2V10z" />
            </svg>
            预警
          </em>
        </div>
        <div class="kind-nums">
          <span>{{ formatCount(kind.totalCount) }} 条</span>
          <span>{{ formatBytes(kind.totalBytes) }}</span>
        </div>
        <div class="mini-track">
          <i
            :style="{
              width: pct(kind.totalCount, overview?.countThreshold ?? 10000) + '%',
              background: kind.countAlert || kind.bytesAlert
                ? undefined
                : `linear-gradient(90deg, ${kind.color}, color-mix(in srgb, ${kind.color} 55%, #fff))`,
            }"
            :class="{ hazard: kind.countAlert || kind.bytesAlert }"
          >
            <span v-if="kind.countAlert || kind.bytesAlert" class="chevrons" aria-hidden="true"><<<<<<<<</span>
          </i>
        </div>
        <div class="kind-pct">
          {{ pct(kind.totalCount, overview?.countThreshold ?? 10000).toFixed(1) }}% / 条数阈值
        </div>
      </article>
    </div>

    <div v-if="loading" class="empty">加载体量曲线…</div>
    <template v-else>
      <p v-if="(overview?.totalCount ?? 0) === 0" class="empty">
        暂无上传记录。上传后将按七类计入年/月曲线；触及 1 万条或 10 GB 时触发预警。
      </p>
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
const bytesPct = computed(() =>
  pct(overview.value?.totalBytes ?? 0, overview.value?.bytesThreshold ?? 10 * 1024 * 1024 * 1024),
)

const alertLevel = computed(() => {
  const peak = Math.max(countPct.value, bytesPct.value)
  if (peak >= 100 || hasAlert.value) return peak >= 100 ? 'critical' : 'high'
  if (peak >= 80) return 'high'
  if (peak >= 60) return 'warn'
  return 'info'
})

const alertLevelLabel = computed(() => {
  return (
    {
      critical: '严重超限',
      high: '高位预警',
      warn: '接近阈值',
      info: '关注',
    } as Record<string, string>
  )[alertLevel.value]
})

const chartTitle = computed(() =>
  metric.value === 'count'
    ? granularity.value === 'year'
      ? '七类数据年条数'
      : `${year.value} 年七类数据月条数`
    : granularity.value === 'year'
      ? '七类数据年容量'
      : `${year.value} 年七类数据月容量`,
)

const chartThreshold = computed(() => {
  if (metric.value === 'count') return overview.value?.countThreshold ?? 10000
  return gb(overview.value?.bytesThreshold ?? 10 * 1024 * 1024 * 1024)
})

const chartThresholdLabel = computed(() =>
  metric.value === 'count' ? '预警 10,000 条' : '预警 10 GB',
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
  })),
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

function fillTone(p: number, alert: boolean) {
  if (alert || p >= 100) return 'tone-critical'
  if (p >= 80) return 'tone-high'
  if (p >= 60) return 'tone-warn'
  if (p >= 30) return 'tone-mid'
  return 'tone-low'
}

function gaugeClass(p: number, alert: boolean) {
  return {
    alert: alert || p >= 100,
    warn: !alert && p >= 60 && p < 100,
  }
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
  color: #0c4a6e;
  border: 1px solid rgba(56, 189, 248, 0.45);
  background:
    radial-gradient(900px 260px at 8% -15%, rgba(125, 211, 252, 0.55), transparent 55%),
    radial-gradient(700px 240px at 95% 110%, rgba(147, 197, 253, 0.5), transparent 52%),
    radial-gradient(420px 180px at 50% 40%, rgba(186, 230, 253, 0.35), transparent 65%),
    linear-gradient(160deg, #e0f2fe 0%, #bae6fd 38%, #7dd3fc 68%, #e0f2fe 100%);
  box-shadow:
    0 18px 40px rgba(14, 165, 233, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    inset 0 0 60px rgba(56, 189, 248, 0.12);
}

.volume.danger.volume.danger {
  border-color: rgba(248, 113, 113, 0.45);
  box-shadow:
    0 0 0 1px rgba(185, 28, 28, 0.35),
    0 22px 48px rgba(80, 0, 0, 0.18),
    inset 0 1px 0 rgba(180, 240, 255, 0.08);
}

.scan {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(14, 116, 144, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(14, 116, 144, 0.08) 1px, transparent 1px),
    radial-gradient(circle at 20% 30%, rgba(56, 189, 248, 0.18), transparent 42%),
    radial-gradient(circle at 80% 70%, rgba(59, 130, 246, 0.12), transparent 45%);
  background-size: 28px 28px, 28px 28px, 100% 100%, 100% 100%;
  mask-image: linear-gradient(180deg, #000 0%, transparent 90%);
  pointer-events: none;
  animation: drift 18s linear infinite;
}

.volume::before.volume::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.45), transparent 22%),
    linear-gradient(270deg, rgba(186, 230, 253, 0.35), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.35), transparent 14%);
  opacity: 0.85;
  z-index: 0;
}

.head,
.controls,
.gauges,
.kind-grid,
.alert-banner {
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
  color: #0369a1;
  font-size: 11px;
  letter-spacing: 0.16em;
  font-weight: 700;
}

.head h3 {
  margin: 6px 0 0;
  font-size: 20px;
  color: #0c4a6e;
}

.sub {
  margin: 8px 0 0;
  max-width: 640px;
  color: #0369a1;
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
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(14, 165, 233, 0.35);
  box-shadow: inset 0 0 10px rgba(125, 211, 252, 0.25);
}

.pills button,
select {
  border: 0;
  background: transparent;
  color: #0e7490;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.pills button.on {
  background: linear-gradient(135deg, #0369a1, #0284c7 55%, #0ea5e9);
  color: #fff;
  box-shadow: 0 0 14px rgba(14, 165, 233, 0.35);
}

select {
  border: 1px solid rgba(56, 189, 248, 0.32);
  background: rgba(7, 32, 68, 0.78);
}

/* —— 预警条：警戒斜纹 + 图标 —— */
.alert-banner {
  display: grid;
  grid-template-columns: 28px auto 1fr auto 28px;
  gap: 12px;
  align-items: center;
  margin-top: 14px;
  padding: 12px 10px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(251, 191, 36, 0.45);
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.92), rgba(30, 20, 10, 0.92)),
    repeating-linear-gradient(
      -45deg,
      rgba(251, 191, 36, 0.18) 0 10px,
      rgba(185, 28, 28, 0.22) 10px 20px
    );
  color: #ffedd5;
  box-shadow:
    0 0 0 1px rgba(248, 113, 113, 0.2),
    0 12px 28px rgba(127, 29, 29, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.alert-banner[data-level='critical'] {
  border-color: rgba(248, 113, 113, 0.65);
  background:
    linear-gradient(90deg, rgba(40, 8, 8, 0.95), rgba(20, 10, 8, 0.94)),
    repeating-linear-gradient(
      -45deg,
      rgba(248, 113, 113, 0.28) 0 10px,
      rgba(127, 29, 29, 0.35) 10px 20px
    );
}

.alert-banner[data-level='high'] {
  border-color: rgba(251, 146, 60, 0.55);
}

.alert-chevron {
  align-self: stretch;
  min-height: 48px;
  background:
    repeating-linear-gradient(
      -45deg,
      rgba(251, 191, 36, 0.95) 0 8px,
      rgba(15, 23, 42, 0.92) 8px 16px
    );
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.25);
  border-radius: 8px;
}

.alert-chevron.mirror {
  background:
    repeating-linear-gradient(
      45deg,
      rgba(251, 191, 36, 0.95) 0 8px,
      rgba(15, 23, 42, 0.92) 8px 16px
    );
}

.alert-banner[data-level='critical'] .alert-chevron {
  background:
    repeating-linear-gradient(
      -45deg,
      #f87171 0 8px,
      #111827 8px 16px
    );
}

.alert-banner[data-level='critical'] .alert-chevron.mirror {
  background:
    repeating-linear-gradient(
      45deg,
      #f87171 0 8px,
      #111827 8px 16px
    );
}

.alert-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.45);
  box-shadow: 0 0 18px rgba(251, 191, 36, 0.25);
  animation: pulse-warn 1.8s ease-in-out infinite;
}

.alert-banner[data-level='critical'] .alert-icon {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.55);
  background: rgba(248, 113, 113, 0.14);
  box-shadow: 0 0 18px rgba(248, 113, 113, 0.35);
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.alert-title strong {
  font-size: 13px;
  letter-spacing: 0.04em;
  color: #fff7ed;
}

.alert-chip {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  color: #111827;
  background: linear-gradient(90deg, #fbbf24, #f59e0b);
}

.alert-banner[data-level='critical'] .alert-chip {
  color: #fff;
  background: linear-gradient(90deg, #ef4444, #b91c1c);
}

.alert-text {
  display: block;
  font-size: 12px;
  line-height: 1.5;
  color: #fed7aa;
}

.alert-pct {
  text-align: right;
  min-width: 72px;
}

.alert-pct em {
  display: block;
  font-style: normal;
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 12px rgba(251, 191, 36, 0.35);
}

.alert-pct small {
  color: #fdba74;
  font-size: 11px;
}

/* —— 进度条 —— */
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
  background: linear-gradient(165deg, rgba(255, 255, 255, 0.78), rgba(224, 242, 254, 0.9));
  border: 1px solid rgba(56, 189, 248, 0.35);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 8px 18px rgba(14, 165, 233, 0.12);
}

.gauge.warn {
  border-color: rgba(251, 191, 36, 0.35);
  background: linear-gradient(180deg, rgba(120, 80, 10, 0.2), rgba(8, 16, 22, 0.7));
}

.gauge.alert,
.kind-card.alert {
  border-color: rgba(248, 113, 113, 0.45);
  background: linear-gradient(180deg, rgba(127, 29, 29, 0.28), rgba(8, 16, 22, 0.7));
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
  color: #0369a1;
  font-size: 12px;
}

.gauge-top b {
  font-size: 22px;
  color: #0c4a6e;
  font-variant-numeric: tabular-nums;
}

.gauge p {
  margin: 8px 0 0;
  color: #0e7490;
  font-size: 12px;
}

.track,
.mini-track {
  position: relative;
  margin-top: 10px;
  height: 16px;
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.7), rgba(224, 242, 254, 0.9)),
    rgba(186, 230, 253, 0.45);
  border: 1px solid rgba(56, 189, 248, 0.28);
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.35);
}

.mini-track {
  height: 10px;
}

.fill {
  position: relative;
  display: block;
  height: 100%;
  border-radius: inherit;
  overflow: hidden;
  transition: width 0.45s ease;
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.25);
}

.fill .chevrons,
.mini-track i .chevrons {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  padding-left: 6px;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: -2px;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
  animation: march 1.1s linear infinite;
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.25);
  pointer-events: none;
}

.mini-track i .chevrons {
  font-size: 11px;
  letter-spacing: -1px;
}

.pct-badge {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  font-weight: 800;
  color: #0c4a6e;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.8);
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}

.tone-low {
  background: linear-gradient(90deg, #22d3ee, #38bdf8 55%, #60a5fa);
}
.tone-mid {
  background: linear-gradient(90deg, #34d399, #22d3ee 50%, #38bdf8);
}
.tone-warn {
  background: linear-gradient(90deg, #fbbf24, #f59e0b 45%, #fb923c);
  box-shadow: 0 0 14px rgba(245, 158, 11, 0.35);
}
.tone-high {
  background: linear-gradient(90deg, #fb923c, #f97316 40%, #ef4444);
  box-shadow: 0 0 14px rgba(239, 68, 68, 0.3);
}
.tone-critical {
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.12), transparent 30%),
    repeating-linear-gradient(
      -45deg,
      #ef4444 0 8px,
      #991b1b 8px 16px
    );
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.4);
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
  color: #0c4a6e;
}

.kind-card em {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  color: #fff7ed;
  background: linear-gradient(90deg, #b45309, #b91c1c);
  border-radius: 999px;
  padding: 2px 7px;
  box-shadow: 0 0 10px rgba(185, 28, 28, 0.35);
}

.kind-nums {
  margin-top: 10px;
  color: #0e7490;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.mini-track i {
  display: block;
  position: relative;
  height: 100%;
  overflow: hidden;
  border-radius: inherit;
}

.mini-track i.hazard {
  background:
    repeating-linear-gradient(
      -45deg,
      #f59e0b 0 6px,
      #b91c1c 6px 12px
    );
}

.kind-pct {
  margin-top: 6px;
  font-size: 11px;
  color: #0e7490;
  font-variant-numeric: tabular-nums;
}

.empty {
  color: #0369a1;
  text-align: center;
  padding: 28px 0;
}

.note {
  position: relative;
  z-index: 1;
  margin: 10px 0 4px;
  color: #0284c7;
  font-size: 12px;
}

@keyframes drift {
  to {
    background-position: 24px 24px;
  }
}

@keyframes march {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-18px);
  }
}

@keyframes pulse-warn {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.85;
  }
}

@media (max-width: 1200px) {
  .kind-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 800px) {
  .gauges,
  .kind-grid {
    grid-template-columns: 1fr;
  }

  .head {
    display: grid;
  }

  .alert-banner {
    grid-template-columns: 22px auto 1fr;
    grid-template-rows: auto auto;
  }

  .alert-pct,
  .alert-chevron.mirror {
    display: none;
  }
}
</style>
