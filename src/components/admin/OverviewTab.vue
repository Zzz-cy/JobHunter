<template>
  <div>
    <div class="stats-grid">
      <StatCard type="info" label="总请求数" :value="metrics.total" />
      <StatCard type="success" label="成功率" :value="metrics.successRate + '%'" :sub="'成功 ' + metrics.success + ' / 失败 ' + metrics.failed" />
      <StatCard type="warning" label="P50延迟" :value="metrics.p50 + 's'" />
      <StatCard type="warning" label="P99延迟" :value="metrics.p99 + 's'" />
      <StatCard label="活跃会话" :value="metrics.activeSessions" />
      <StatCard label="活跃用户" :value="metrics.activeUsers" />
    </div>
    <div class="chart-grid">
      <div class="chart-card">
        <h3>请求趋势（最近24小时）</h3>
        <BarChart :data="requestTrendData" />
      </div>
      <div class="chart-card">
        <h3>响应时间分布</h3>
        <BarChart :data="latencyData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatCard from '../common/StatCard.vue'
import BarChart from '../common/BarChart.vue'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const metrics = computed(() => {
  const d = props.data.data || props.data
  const req = d.requests || {}
  const total = req.total || 0
  const success = req.success || 0
  const failed = req.failed || 0
  const successRate = total > 0 ? (success / total * 100).toFixed(1) : 0
  return {
    total,
    success,
    failed,
    successRate,
    p50: (req.p50_latency || 0).toFixed(2),
    p99: (req.p99_latency || 0).toFixed(2),
    activeSessions: d.active_sessions || 0,
    activeUsers: d.active_users || 0,
  }
})

const requestTrendData = [
  { label: '0-4h', value: Math.floor(Math.random() * 50 + 10), color: '#667eea' },
  { label: '4-8h', value: Math.floor(Math.random() * 80 + 20), color: '#667eea' },
  { label: '8-12h', value: Math.floor(Math.random() * 120 + 40), color: '#667eea' },
  { label: '12-16h', value: Math.floor(Math.random() * 100 + 30), color: '#667eea' },
  { label: '16-20h', value: Math.floor(Math.random() * 90 + 25), color: '#667eea' },
  { label: '20-24h', value: Math.floor(Math.random() * 40 + 5), color: '#667eea' },
]

const latencyData = [
  { label: '<1s', value: 60, color: '#10b981' },
  { label: '1-3s', value: 25, color: '#3b82f6' },
  { label: '3-5s', value: 10, color: '#f59e0b' },
  { label: '5-10s', value: 4, color: '#f97316' },
  { label: '>10s', value: 1, color: '#ef4444' },
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

.chart-card h3 {
  font-size: 15px;
  color: #333;
  margin-bottom: 16px;
}
</style>
