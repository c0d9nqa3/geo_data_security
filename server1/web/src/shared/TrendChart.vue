<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  color: string
  unit?: string
  points: { date: string; count: number }[]
}>()

const width = 640
const height = 220
const pad = { l: 36, r: 16, t: 18, b: 36 }

const series = computed(() => props.points ?? [])
const maxVal = computed(() => Math.max(1, ...series.value.map((p) => p.count)))

const coords = computed(() => {
  const innerW = width - pad.l - pad.r
  const innerH = height - pad.t - pad.b
  const n = Math.max(series.value.length - 1, 1)
  return series.value.map((p, i) => {
    const x = pad.l + (innerW * i) / n
    const y = pad.t + innerH * (1 - p.count / maxVal.value)
    return { ...p, x, y, label: p.date.slice(5) }
  })
})

const linePath = computed(() => {
  const pts = coords.value
  if (!pts.length) return ''
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i]
    const b = pts[i + 1]
    const cx = (a.x + b.x) / 2
    d += ` C ${cx} ${a.y}, ${cx} ${b.y}, ${b.x} ${b.y}`
  }
  return d
})

const areaPath = computed(() => {
  const pts = coords.value
  if (!pts.length) return ''
  const base = height - pad.b
  return `${linePath.value} L ${pts[pts.length - 1].x} ${base} L ${pts[0].x} ${base} Z`
})

const total = computed(() => series.value.reduce((s, p) => s + p.count, 0))
const gid = computed(() => `glow-${props.color.replace('#', '')}`)
</script>

<template>
  <div class="chart-card">
    <div class="chart-head">
      <div>
        <p class="kicker">近 7 日趋势</p>
        <h3>{{ title }}</h3>
      </div>
      <div class="sum">
        <strong>{{ total }}</strong>
        <span>{{ unit || '合计' }}</span>
      </div>
    </div>
    <svg class="chart" :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="title">
      <defs>
        <linearGradient :id="`${gid}-fill`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="color" stop-opacity="0.38" />
          <stop offset="100%" :stop-color="color" stop-opacity="0.02" />
        </linearGradient>
        <filter :id="`${gid}-blur`" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3.5" />
        </filter>
      </defs>
      <g class="grid">
        <line
          v-for="g in 4"
          :key="g"
          :x1="pad.l"
          :x2="width - pad.r"
          :y1="pad.t + ((height - pad.t - pad.b) * (g - 1)) / 3"
          :y2="pad.t + ((height - pad.t - pad.b) * (g - 1)) / 3"
        />
      </g>
      <path :d="areaPath" :fill="`url(#${gid}-fill)`" />
      <path :d="linePath" fill="none" :stroke="color" stroke-width="3" opacity="0.28" :filter="`url(#${gid}-blur)`" />
      <path :d="linePath" fill="none" :stroke="color" stroke-width="2.4" stroke-linecap="round" />
      <g v-for="p in coords" :key="p.date">
        <circle :cx="p.x" :cy="p.y" r="8" :fill="color" opacity="0.12" />
        <circle :cx="p.x" :cy="p.y" r="3.4" :fill="color" stroke="#fff" stroke-width="1.5" />
        <text :x="p.x" :y="height - 12" text-anchor="middle">{{ p.label }}</text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.chart-card {
  height: 100%;
}

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 6px;
}

.kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #5f8aa3;
}

h3 {
  margin: 4px 0 0;
  font-size: 16px;
  color: #123047;
}

.sum {
  text-align: right;
}

.sum strong {
  display: block;
  font-size: 22px;
  color: #0f766e;
  line-height: 1;
}

.sum span {
  font-size: 11px;
  color: #6b8798;
}

.chart {
  width: 100%;
  height: 210px;
  display: block;
}

.grid line {
  stroke: rgba(15, 76, 110, 0.1);
  stroke-dasharray: 3 5;
}

text {
  fill: #7a93a6;
  font-size: 11px;
}
</style>
