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
  const lat = req.latency || {}
  const total = req.total || 0
  const errors = req.errors || 0
  const success = Math.max(total - errors, 0)
  const successRate = total > 0 ? (success / total * 100).toFixed(1) : 0
  return {
    total,
    success,
    failed: errors,
    successRate,
    p50: (lat.p50 || 0).toFixed(2),
    p99: (lat.p99 || 0).toFixed(2),
    activeSessions: d.active_sessions || 0,
    activeUsers: d.active_users || 0,
  }
})

const TREND_COLORS = { success: '#10b981', warning: '#f59e0b', danger: '#ef4444' }
const bucketColor = (label) =>
  label.includes('10s') || label.includes('>10') ? TREND_COLORS.danger
    : label.includes('5-10') ? '#f97316'
      : label.includes('3-5') ? TREND_COLORS.warning
        : TREND_COLORS.success

const requestTrendData = computed(() => {
  const d = props.data.data || props.data
  return (d.request_trend || []).map(t => ({ label: t.label, value: t.count || 0, color: '#667eea' }))
})

const latencyData = computed(() => {
  const d = props.data.data || props.data
  return (d.latency_buckets || []).map(b => ({ label: b.label, value: b.count || 0, color: bucketColor(b.label) }))
})
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
