<template>
  <div>
    <div class="section-header">
      <h2>LLM模型统计</h2>
      <button class="refresh-btn" @click="$emit('refresh')">🔄 刷新</button>
    </div>
    <div class="stats-grid">
      <StatCard type="info" label="总调用次数" :value="stats.totalCalls" />
      <StatCard label="总Token消耗" :value="stats.totalTokens + 'K'" />
      <StatCard type="warning" label="总成本" :value="'¥' + stats.totalCost" />
      <StatCard label="平均延迟" :value="stats.avgLatency + 's'" />
    </div>
    <div class="chart-grid">
      <div class="chart-card">
        <h3>Token消耗趋势</h3>
        <BarChart :data="tokenData" />
      </div>
      <div class="chart-card">
        <h3>成本分布</h3>
        <BarChart :data="costData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatCard from '../common/StatCard.vue'
import BarChart from '../common/BarChart.vue'

defineEmits(['refresh'])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const stats = computed(() => {
  const d = props.data.data || props.data
  const llm = d.llm || {}
  return {
    totalCalls: llm.total_calls || 0,
    totalTokens: ((llm.total_tokens || 0) / 1000).toFixed(1),
    totalCost: (llm.total_cost || 0).toFixed(2),
    avgLatency: (llm.avg_latency || 0).toFixed(2),
  }
})

const tokenData = [
  { label: 'glm-4-flash', value: 45, color: '#667eea' },
  { label: 'glm-4-air', value: 30, color: '#764ba2' },
  { label: 'deepseek', value: 15, color: '#3b82f6' },
  { label: 'qwen', value: 10, color: '#10b981' },
]

const costData = [
  { label: 'glm-4-flash', value: 0.5, color: '#667eea' },
  { label: 'glm-4-air', value: 1.2, color: '#764ba2' },
  { label: 'deepseek', value: 0.3, color: '#3b82f6' },
  { label: 'qwen', value: 0.2, color: '#10b981' },
]
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.chart-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.chart-card h3 { font-size: 15px; color: #333; margin-bottom: 16px; }
</style>
