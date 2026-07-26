<template>
  <div class="bar-chart">
    <div v-for="(item, i) in data" :key="i" class="bar-item">
      <div class="bar-value">{{ formatValue(item.value) }}</div>
      <div
        class="bar"
        :style="{ height: (item.value / maxVal * 160) + 'px', background: item.color || '#667eea' }"
      ></div>
      <div class="bar-label">{{ item.label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const maxVal = computed(() => Math.max(...props.data.map(d => d.value), 1))

function formatValue(val) {
  if (typeof val === 'number' && val > 100) return (val / 1000).toFixed(1) + 'K'
  return val
}
</script>

<style scoped>
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 200px;
  padding-top: 20px;
}

.bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.bar {
  width: 100%;
  max-width: 50px;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s;
  min-height: 2px;
}

.bar-label {
  font-size: 11px;
  color: #999;
  text-align: center;
  word-break: break-all;
}

.bar-value {
  font-size: 11px;
  color: #666;
  font-weight: 600;
}
</style>
