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
        <h3>Token消耗分布</h3>
        <BarChart :data="tokenData" />
      </div>
      <div class="chart-card">
        <h3>成本分布</h3>
        <BarChart :data="costData" />
      </div>
    </div>
    <div class="data-table">
      <table>
        <thead>
          <tr>
            <th>模型</th><th>调用次数</th><th>成功率</th>
            <th>平均耗时</th><th>输入Token</th><th>输出Token</th><th>成本</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in modelRows" :key="m.name">
            <td>{{ m.label }}</td>
            <td>{{ m.calls }}</td>
            <td><StatusBadge :type="m.rateClass">{{ m.successRate }}%</StatusBadge></td>
            <td>{{ m.avgLatency }}s</td>
            <td>{{ m.tokensIn }}</td>
            <td>{{ m.tokensOut }}</td>
            <td>¥{{ m.cost }}</td>
          </tr>
          <tr v-if="!modelRows.length">
            <td colspan="7" class="table-empty">暂无 LLM 调用记录</td>
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
import BarChart from '../common/BarChart.vue'

defineEmits(['refresh'])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

// 跨厂商模型 → 展示名(与 llm_module config 的 provider 对应)
const MODEL_LABELS = {
  'glm-4-flash': 'GLM-4-Flash(智谱)', 'glm-4-air': 'GLM-4-Air(智谱)',
  'glm-4': 'GLM-4(智谱)', 'glm-4-plus': 'GLM-4-Plus(智谱)',
  'glm-4-long': 'GLM-4-Long(智谱)', 'glm-4-alltools': 'GLM-4-AllTools(智谱)',
  'deepseek-chat': 'DeepSeek', 'moonshot-v1-8k': 'Kimi(Moonshot)',
  'gpt-4o-mini': '通义(GPT-4o-mini)', 'generalv3.5': '讯飞星火',
}

// tokens/cost 字段在 llm 指标里是 {count,avg,...} 统计对象: 总量 ≈ avg×count
const statTotal = (x) => {
  if (typeof x === 'number') return x
  if (x && typeof x.avg === 'number' && typeof x.count === 'number') return Math.round(x.avg * x.count)
  if (x && typeof x.total === 'number') return x.total
  return 0
}

// 每模型归一为 [{name,label,calls,success,failed,successRate,avgLatency,tokensIn,tokensOut,cost,rateClass}]
const modelRows = computed(() => {
  const d = props.data.data || props.data
  const llm = d.llm || {}
  return Object.entries(llm).map(([name, m]) => {
    const calls = m.total_calls || 0
    const success = m.success || 0
    const successRate = calls > 0 ? (success / calls * 100) : 0
    const avgLatency = m.latency && typeof m.latency.avg === 'number' ? m.latency.avg : 0
    const tokensIn = statTotal(m.tokens_input)
    const tokensOut = statTotal(m.tokens_output)
    // cost 是 {count,avg,...}(¥/次): 总量 = avg×count, 保留小数别取整
    const cost = typeof m.cost === 'number' ? m.cost
      : (m.cost && typeof m.cost.avg === 'number' ? m.cost.avg * (m.cost.count || 1) : 0)
    const rateClass = successRate >= 90 ? 'success' : successRate >= 70 ? 'warning' : 'danger'
    return {
      name,
      label: MODEL_LABELS[name] || name,
      calls, success, successRate: successRate.toFixed(1),
      avgLatency: avgLatency.toFixed(2),
      tokensIn, tokensOut,
      cost: cost.toFixed(4),
      rateClass,
    }
  }).sort((a, b) => b.calls - a.calls)
})

const stats = computed(() => {
  const rows = modelRows.value
  const totalCalls = rows.reduce((s, r) => s + r.calls, 0)
  const totalTokens = rows.reduce((s, r) => s + r.tokensIn + r.tokensOut, 0)
  const totalCost = rows.reduce((s, r) => s + Number(r.cost), 0)
  const latencySum = rows.reduce((s, r) => s + r.calls * Number(r.avgLatency), 0)
  const avgLatency = totalCalls > 0 ? (latencySum / totalCalls) : 0
  return {
    totalCalls,
    totalTokens: (totalTokens / 1000).toFixed(1),
    totalCost: totalCost.toFixed(2),
    avgLatency: avgLatency.toFixed(2),
  }
})

const COLORS = ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#0ea5e9', '#f97316', '#6b7280']

const tokenData = computed(() =>
  modelRows.value.map((m, i) => ({ label: m.label, value: m.tokensIn + m.tokensOut, color: COLORS[i % COLORS.length] })))

const costData = computed(() =>
  modelRows.value.map((m, i) => ({ label: m.label, value: Number(m.cost), color: COLORS[i % COLORS.length] })))
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
.data-table tr:hover td { background: #f8f9fa; }
.table-empty { text-align: center; color: #999; padding: 24px; }
</style>
