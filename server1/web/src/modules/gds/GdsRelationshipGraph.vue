<template>
  <div class="graph-wrap">
    <svg v-if="layout.nodes.length" :viewBox="viewBox" class="graph-svg" role="img">
      <defs>
        <marker id="gds-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6 Z" fill="var(--text-muted, #888)" />
        </marker>
      </defs>
      <line
        v-for="(e, i) in layout.edges"
        :key="'e' + i"
        :x1="e.x1"
        :y1="e.y1"
        :x2="e.x2"
        :y2="e.y2"
        class="edge"
        marker-end="url(#gds-arrow)"
      />
      <g v-for="n in layout.nodes" :key="n.id">
        <rect
          :x="n.x - n.w / 2"
          :y="n.y - n.h / 2"
          :width="n.w"
          :height="n.h"
          rx="6"
          class="node-box"
        />
        <text :x="n.x" :y="n.y + 4" text-anchor="middle" class="node-label">{{ n.label }}</text>
      </g>
    </svg>
    <p v-else class="empty">暂无节点，请查看下方原始数据。</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Json = Record<string, unknown>

const props = defineProps<{ data: Json | null }>()

interface LayoutNode {
  id: string
  label: string
  x: number
  y: number
  w: number
  h: number
}

function nodeList(raw: Json): { id: string; label: string }[] {
  const arr = raw.nodes ?? raw.vertices
  if (!Array.isArray(arr)) return []
  return arr.map((item, i) => {
    const o = (item ?? {}) as Json
    const id = String(o.id ?? o.key ?? o.name ?? i)
    const label = String(o.label ?? o.title ?? o.name ?? id)
    return { id, label }
  })
}

function edgeList(raw: Json): { from: string; to: string }[] {
  const arr = raw.edges ?? raw.links
  if (!Array.isArray(arr)) return []
  return arr
    .map((item) => {
      const o = (item ?? {}) as Json
      const from = String(o.source ?? o.from ?? o.start ?? '')
      const to = String(o.target ?? o.to ?? o.end ?? '')
      if (!from || !to) return null
      return { from, to }
    })
    .filter(Boolean) as { from: string; to: string }[]
}

const layout = computed(() => {
  const raw = props.data
  if (!raw) return { nodes: [] as LayoutNode[], edges: [] as { x1: number; y1: number; x2: number; y2: number }[] }
  const ids = nodeList(raw)
  const edges = edgeList(raw)
  const w = 120
  const h = 36
  const gap = 24
  const nodes: LayoutNode[] = ids.map((n, i) => ({
    ...n,
    x: 80 + i * (w + gap),
    y: 60,
    w,
    h,
  }))
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const edgeGeom = edges
    .map((e) => {
      const a = byId.get(e.from)
      const b = byId.get(e.to)
      if (!a || !b) return null
      return { x1: a.x + a.w / 2, y1: a.y, x2: b.x - b.w / 2, y2: b.y }
    })
    .filter(Boolean) as { x1: number; y1: number; x2: number; y2: number }[]
  return { nodes, edges: edgeGeom }
})

const viewBox = computed(() => {
  const n = layout.value.nodes.length
  const width = Math.max(320, 80 + n * 144)
  return `0 0 ${width} 120`
})
</script>

<style scoped>
.graph-wrap {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.5rem;
  background: var(--bg-panel, var(--surface));
  overflow-x: auto;
}
.graph-svg {
  width: 100%;
  min-height: 120px;
}
.edge {
  stroke: var(--text-muted, #888);
  stroke-width: 1.5;
}
.node-box {
  fill: var(--surface);
  stroke: var(--accent, #3b82f6);
  stroke-width: 1.5;
}
.node-label {
  font-size: 10px;
  fill: var(--text, #eee);
}
.empty {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
}
</style>
