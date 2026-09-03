<template>
  <div>
    <div class="section-header">
      <h2>意图识别统计</h2>
      <button class="refresh-btn" @click="$emit('refresh')">🔄 刷新</button>
    </div>
    <div class="stats-grid">
      <StatCard type="info" label="意图识别请求" :value="totalIntents" />
      <StatCard type="success" label="高置信占比" :value="highConfidenceRate + '%'" />
      <StatCard type="warning" label="低置信率" :value="lowConfidenceRate + '%'" />
    </div>
    <div class="chart-grid">
      <div class="chart-card">
        <h3>意图分布</h3>
        <PieChart :items="pieItems" />
      </div>
      <div class="chart-card">
        <h3>置信度分布</h3>
        <BarChart :data="confidenceData" />
      </div>
    </div>
    <div class="data-table">
      <table>
        <thead>
          <tr><th>意图</th><th>次数</th><th>占比</th><th>分布</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in pieItems" :key="item.key">
            <td>{{ item.label }}</td>
            <td>{{ item.count }}</td>
            <td>{{ item.percent }}%</td>
            <td><ProgressBar :value="item.percent" color-class="green" /></td>
          </tr>
          <tr v-if="!pieItems.length">
            <td colspan="4" class="table-empty">暂无意图识别记录</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatCard from '../common/StatCard.vue'
import BarChart from '../common/BarChart.vue'
import PieChart from '../common/PieChart.vue'
import ProgressBar from '../common/ProgressBar.vue'

defineEmits(['refresh'])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const INTENT_NAMES = {
  job_analysis: '岗位分析', skill_gap: '差距分析', learning_path: '学习规划',
  trend_prediction: '趋势预测', job_compare: '岗位对比', resume_match: '简历匹配',
  report_generation: '报告生成', general_qa: '通用问答',
}

const COLORS = ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#6b7280']

const intentStats = computed(() => {
  const d = props.data.data || props.data
  const intents = d.intents || {}
  const distribution = intents.distribution || {}
  // 真实结构: {general_qa: {count, percentage}, ...}(老格式可能是裸数字, 兼容两者)
  const entries = Object.entries(distribution).map(([key, v]) => {
    const count = v && typeof v === 'object' ? (Number(v.count) || 0) : (Number(v) || 0)
    const pct = v && typeof v === 'object' && typeof v.percentage === 'number' ? v.percentage : null
    return { key, count, pct }
  })
  const total = intents.total || entries.reduce((s, e) => s + e.count, 0)
  const items = entries.map((e, idx) => ({
    key: e.key,
    label: INTENT_NAMES[e.key] || e.key,
    count: e.count,
    percent: e.pct !== null ? e.pct * 100 : (total > 0 ? (e.count / total * 100) : 0),
    color: COLORS[idx % COLORS.length],
  }))
  return {
    total,
    distribution: items,
    lowConfidenceRate: typeof intents.low_confidence_rate === 'number' ? intents.low_confidence_rate : 0,
  }
})

const totalIntents = computed(() => intentStats.value.total)
const lowConfidenceRate = computed(() => (intentStats.value.lowConfidenceRate * 100).toFixed(1))
const highConfidenceRate = computed(() => (100 - Number(lowConfidenceRate.value)).toFixed(1))

const pieItems = computed(() =>
  intentStats.value.distribution
    .sort((a, b) => b.count - a.count)
    .map(item => ({ ...item, percent: Number(item.percent || 0).toFixed(1) })))

const confidenceData = computed(() => {
  const d = props.data.data || props.data
  const buckets = d.intent_confidence_buckets || []
  const color = (label) =>
    label.includes('0.8') ? '#10b981' : label.includes('0.6') ? '#3b82f6'
      : label.includes('0.5') ? '#f59e0b' : '#ef4444'
  return buckets.map(b => ({ label: b.label, value: b.count || 0, color: color(b.label) }))
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

.chart-card h3 { font-size: 15px; color: #333; margin-bottom: 16px; }

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
.data-table td { padding: 12px 16px; font-size: 13px; color: #333; border-bottom: 1px solid #f0f0f0; }
.table-empty { text-align: center; color: #999; padding: 24px; }
</style>
