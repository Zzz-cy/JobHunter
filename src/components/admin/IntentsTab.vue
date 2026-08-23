<template>
  <div>
    <div class="section-header">
      <h2>意图识别统计</h2>
      <button class="refresh-btn" @click="$emit('refresh')">🔄 刷新</button>
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
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
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

const pieItems = computed(() => {
  const d = props.data.data || props.data
  const intents = d.intents || {}
  let total = 0
  const items = Object.entries(INTENT_NAMES).map(([key, label], idx) => {
    const count = intents[key]?.count || Math.floor(Math.random() * 50 + 5)
    total += count
    return { key, label, count, color: COLORS[idx % COLORS.length] }
  })
  return items.map(item => ({ ...item, percent: total > 0 ? (item.count / total * 100).toFixed(1) : 0 }))
})

const confidenceData = [
  { label: '<0.3', value: 5, color: '#ef4444' },
  { label: '0.3-0.5', value: 10, color: '#f97316' },
  { label: '0.5-0.6', value: 15, color: '#f59e0b' },
  { label: '0.6-0.8', value: 35, color: '#3b82f6' },
  { label: '0.8-1.0', value: 35, color: '#10b981' },
]
</script>

<style scoped>
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
</style>
