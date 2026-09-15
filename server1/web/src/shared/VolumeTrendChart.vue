<script setup lang="ts">
import { computed, ref } from 'vue'

export interface VolumeSeries {
  code: string
  label: string
  color: string
  alert?: boolean
  points: { period: string; value: number }[]
}

const props = defineProps<{
  title: string
  unit: string
  threshold?: number
  thresholdLabel?: string
  series: VolumeSeries[]
}>()

const width = 960
const height = 278
const pad = { l: 52, r: 18, t: 22, b: 42 }
const hidden = ref<Record<string, boolean>>({})
const hoverIndex = ref<number | null>(null)

const visible = computed(() => props.series.filter((s) => !hidden.value[s.code]))
const periods = computed(() => props.series[0]?.points.map((p) => p.period) ?? [])
const maxVal = computed(() => {
  const dataMax = Math.max(0, ...visible.value.flatMap((s) => s.points.map((p) => p.value)))
  const threshold = props.threshold ?? 0
  const near = threshold > 0 && dataMax >= threshold * 0.12
  return Math.max(1, dataMax, near ? threshold : 0)
})

const showThreshold = computed(() => {
  const threshold = props.threshold ?? 0
  return threshold > 0 && threshold <= maxVal.value
})

const thresholdY = computed(() => {
  const innerH = height - pad.t - pad.b
  return pad.t + innerH * (1 - (props.threshold ?? 0) / maxVal.value)
})

function xAt(i: number, n: number) {
  const innerW = width - pad.l - pad.r
  return pad.l + (innerW * i) / Math.max(n - 1, 1)
}

function yAt(value: number) {
  const innerH = height - pad.t - pad.b
  return pad.t + innerH * (1 - value / maxVal.value)
}

function pathOf(points: { period: string; value: number }[]) {
  if (!points.length) return ''
  const n = points.length
  const mapped = points.map((p, i) => ({ x: xAt(i, n), y: yAt(p.value) }))
  if (mapped.length === 1) return `M ${mapped[0].x} ${mapped[0].y}`
  let d = `M ${mapped[0].x} ${mapped[0].y}`
  for (let i = 0; i < mapped.length - 1; i++) {
    const a = mapped[i]
    const b = mapped[i + 1]
    const cx = (a.x + b.x) / 2
    d += ` C ${cx} ${a.y}, ${cx} ${b.y}, ${b.x} ${b.y}`
  }
  return d
}

function formatTick(period: string) {
  if (period.length === 4) return period
  return period.slice(5)
}

function formatValue(value: number) {
  if (value >= 10000) return `${(value / 10000).toFixed(1)}万`
  if (value >= 1000) return `${Math.round(value)}`
  if (Number.isInteger(value)) return String(value)
  return value.toFixed(2)
}

function toggle(code: string) {
  hidden.value = { ...hidden.value, [code]: !hidden.value[code] }
}

function onMove(event: MouseEvent) {
  const svg = event.currentTarget as SVGSVGElement
  const rect = svg.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * width
  const n = periods.value.length
  if (n <= 0) return
  let best = 0
  let bestDist = Infinity
  for (let i = 0; i < n; i++) {
    const dist = Math.abs(xAt(i, n) - x)
    if (dist < bestDist) {
      best = i
      bestDist = dist
    }
  }
  hoverIndex.value = best
}

const hoverItems = computed(() => {
  const i = hoverIndex.value
  if (i == null) return []
  return visible.value.map((s) => ({
    ...s,
    value: s.points[i]?.value ?? 0,
  }))
})
</script>

<template>
  <div class="vchart">
    <div class="head">
      <div>
        <p class="kicker">MULTI-SPECTRUM · LIVE SERIES</p>
        <h3>{{ title }}</h3>
      </div>
      <div class="legend">
        <button
          v-for="s in series"
          :key="s.code"
          type="button"
          class="leg"
          :class="{ off: hidden[s.code], alert: s.alert }"
          @click="toggle(s.code)"
        >
          <i :style="{ background: s.color }" />
          {{ s.label }}
        </button>
      </div>
    </div>

    <svg
      class="chart"
      :viewBox="`0 0 ${width} ${height}`"
      role="img"
      :aria-label="title"
      @mousemove="onMove"
      @mouseleave="hoverIndex = null"
    >
      <defs>
        <linearGradient id="vol-scan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#6ee7f9" stop-opacity="0.16" />
          <stop offset="100%" stop-color="#6ee7f9" stop-opacity="0" />
        </linearGradient>
        <filter id="vol-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.6" />
        </filter>
      </defs>
      <rect
        :x="pad.l"
        :y="pad.t"
        :width="width - pad.l - pad.r"
        :height="height - pad.t - pad.b"
        fill="url(#vol-scan)"
        opacity="0.35"
      />
      <g class="grid">
        <line
          v-for="g in 5"
          :key="g"
          :x1="pad.l"
          :x2="width - pad.r"
          :y1="pad.t + ((height - pad.t - pad.b) * (g - 1)) / 4"
          :y2="pad.t + ((height - pad.t - pad.b) * (g - 1)) / 4"
        />
      </g>
      <g v-if="showThreshold">
        <line
          class="threshold"
          :x1="pad.l"
          :x2="width - pad.r"
          :y1="thresholdY"
          :y2="thresholdY"
        />
        <text class="th-label" :x="width - pad.r - 4" :y="thresholdY - 6" text-anchor="end">
          {{ thresholdLabel || `预警 ${formatTick(String(threshold))}` }}
        </text>
      </g>
      <g v-for="s in visible" :key="s.code">
        <path :d="pathOf(s.points)" fill="none" :stroke="s.color" stroke-width="4.2" opacity="0.22" filter="url(#vol-glow)" />
        <path
          :d="pathOf(s.points)"
          fill="none"
          :stroke="s.color"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </g>
      <g v-if="hoverIndex != null && periods.length">
        <line
          class="guide"
          :x1="xAt(hoverIndex, periods.length)"
          :x2="xAt(hoverIndex, periods.length)"
          :y1="pad.t"
          :y2="height - pad.b"
        />
        <g v-for="s in visible" :key="`${s.code}-dot`">
          <circle
            :cx="xAt(hoverIndex, periods.length)"
            :cy="yAt(s.points[hoverIndex]?.value ?? 0)"
            r="4.2"
            :fill="s.color"
            stroke="#07141d"
            stroke-width="1.4"
          />
        </g>
      </g>
      <g>
        <text
          v-for="(period, i) in periods"
          :key="period"
          :x="xAt(i, periods.length)"
          :y="height - 12"
          text-anchor="middle"
        >
          {{ formatTick(period) }}
        </text>
      </g>
      <text class="y-max" :x="8" :y="pad.t + 4">{{ formatValue(maxVal) }}</text>
      <text class="y-max" :x="8" :y="height - pad.b">0</text>
    </svg>

    <div v-if="hoverIndex != null && periods[hoverIndex]" class="tip">
      <strong>{{ periods[hoverIndex] }}</strong>
      <span v-for="item in hoverItems" :key="item.code">
        <i :style="{ background: item.color }" />
        {{ item.label }} {{ formatValue(item.value) }} {{ unit }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.vchart {
  position: relative;
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 8px;
}

.kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #7bd7e8;
}

h3 {
  margin: 4px 0 0;
  font-size: 16px;
  color: #e8fbff;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.leg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(125, 211, 232, 0.22);
  background: rgba(7, 28, 40, 0.55);
  color: #d7f6ff;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  cursor: pointer;
}

.leg i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}

.leg.off {
  opacity: 0.35;
}

.leg.alert {
  border-color: #8b0000;
  color: #fecaca;
  background: rgba(139, 0, 0, 0.28);
}

.chart {
  width: 100%;
  height: 268px;
  display: block;
}

.grid line {
  stroke: rgba(125, 211, 232, 0.14);
  stroke-dasharray: 3 6;
}

.threshold {
  stroke: #8b0000;
  stroke-width: 1.8;
  stroke-dasharray: 5 6;
}

.th-label {
  fill: #ff6b6b;
  font-size: 11px;
  font-weight: 700;
}

.guide {
  stroke: rgba(255, 255, 255, 0.35);
  stroke-dasharray: 2 4;
}

text {
  fill: #8fb8c8;
  font-size: 11px;
}

.y-max {
  font-size: 10px;
  fill: #6f98a8;
}

.tip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(4, 16, 24, 0.72);
  border: 1px solid rgba(125, 211, 232, 0.18);
  color: #d7f6ff;
  font-size: 12px;
}

.tip strong {
  color: #7bd7e8;
  margin-right: 6px;
}

.tip span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tip i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
</style>
