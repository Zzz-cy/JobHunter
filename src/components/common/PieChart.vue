<template>
  <div>
    <div
      class="pie-chart"
      :style="{ background: conicGradient }"
    ></div>
    <div class="pie-legend">
      <div v-for="(item, i) in items" :key="i" class="pie-legend-item">
        <div class="pie-legend-dot" :style="{ background: item.color }"></div>
        <span>{{ item.label }} ({{ item.count }})</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  colors: {
    type: Array,
    default: () => ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#6b7280'],
  },
})

const total = computed(() => props.items.reduce((s, i) => s + i.count, 0))

const conicGradient = computed(() => {
  let currentAngle = 0
  const parts = props.items.map((item, idx) => {
    const angle = (item.count / Math.max(total.value, 1)) * 360
    const start = currentAngle
    currentAngle += angle
    const color = item.color || props.colors[idx % props.colors.length]
    return `${color} ${start}deg ${currentAngle}deg`
  })
  return `conic-gradient(${parts.join(', ')})`
})
</script>

<style scoped>
.pie-chart {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  margin: 0 auto;
}

.pie-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  justify-content: center;
}

.pie-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.pie-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
