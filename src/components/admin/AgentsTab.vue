<template>
  <div>
    <div class="section-header">
      <h2>Agent执行统计</h2>
      <button class="refresh-btn" @click="$emit('refresh')">🔄 刷新</button>
    </div>
    <div class="stats-grid">
      <StatCard
        v-for="a in agentStats"
        :key="a.key"
        :type="a.rateClass"
        :label="a.name"
        :value="a.calls"
        :sub="'成功率 ' + a.successRate + '%'"
      />
    </div>
    <div class="data-table">
      <table>
        <thead>
          <tr>
            <th>Agent</th><th>调用次数</th><th>成功率</th>
            <th>平均耗时</th><th>重试次数</th><th>健康度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in agentStats" :key="a.key">
            <td>{{ a.name }}</td>
            <td>{{ a.calls }}</td>
            <td><StatusBadge :type="a.rateClass">{{ a.successRate }}%</StatusBadge></td>
            <td>{{ a.avgLatency }}s</td>
            <td>{{ a.retries }}</td>
            <td><ProgressBar :value="a.successRate" :color-class="a.barClass" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatCard from '../common/StatCard.vue'
import StatusBadge from '../common/StatusBadge.vue'
import ProgressBar from '../common/ProgressBar.vue'

defineEmits(['refresh'])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const AGENT_NAMES = {
  job_analysis: '岗位分析', skill_gap: '差距分析', learning_path: '学习规划',
  trend_prediction: '趋势预测', report_generation: '报告生成',
  job_compare: '岗位对比', resume_match: '简历匹配',
}

const agentStats = computed(() => {
  const d = props.data.data || props.data
  const agentMetrics = d.agents || {}
  return Object.entries(AGENT_NAMES).map(([key, name]) => {
    const m = agentMetrics[key] || {}
    const calls = m.total_calls || 0
    const success = m.success || 0
    const successRate = calls > 0 ? (success / calls * 100) : 0
    const avgLatency = (m.latency && typeof m.latency.avg === 'number' ? m.latency.avg : 0)
    const retries = m.retries || 0
    const rateClass = successRate >= 90 ? 'success' : successRate >= 70 ? 'warning' : 'danger'
    const barClass = successRate >= 90 ? 'green' : successRate >= 70 ? 'yellow' : 'red'
    return { key, name, calls, successRate: successRate.toFixed(1), avgLatency: avgLatency.toFixed(2), retries, rateClass, barClass }
  })
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.data-table {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.data-table table { width: 100%; border-collapse: collapse; }
.data-table th {
  background: #f8f9fa; padding: 12px 16px; text-align: left;
  font-size: 13px; color: #666; font-weight: 600; border-bottom: 1px solid #eee;
}
.data-table td {
  padding: 12px 16px; font-size: 13px; color: #333; border-bottom: 1px solid #f0f0f0;
}
.data-table tr:hover td { background: #f8f9fa; }
</style>
