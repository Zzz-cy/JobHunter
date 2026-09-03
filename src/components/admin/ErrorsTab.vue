<template>
  <div>
    <div class="section-header">
      <h2>错误分析</h2>
      <button class="refresh-btn" @click="$emit('refresh')">🔄 刷新</button>
    </div>
    <div class="stats-grid">
      <StatCard type="danger" label="总错误数" :value="stats.totalErrors" />
      <StatCard type="warning" label="超时错误" :value="stats.timeoutErrors" />
      <StatCard type="warning" label="LLM错误" :value="stats.llmErrors" />
      <StatCard type="danger" label="Agent错误" :value="stats.agentErrors" />
    </div>
    <div v-if="errorRows.length" class="data-table">
      <table>
        <thead><tr><th>级别</th><th>错误类型</th><th>次数</th><th>占比</th></tr></thead>
        <tbody>
          <tr v-for="(row, i) in errorRows" :key="i">
            <td><StatusBadge :type="row.severity">{{ row.severityLabel }}</StatusBadge></td>
            <td>{{ row.type }}</td>
            <td>{{ row.count }}</td>
            <td>{{ row.percent }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="empty-state">
      <div class="icon">✅</div>
      <div class="text">暂无错误记录</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatCard from '../common/StatCard.vue'
import StatusBadge from '../common/StatusBadge.vue'

defineEmits(['refresh'])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const stats = computed(() => {
  const d = props.data.data || props.data
  const err = d.errors || {}
  return {
    totalErrors: err.total || 0,
    timeoutErrors: err.timeout || 0,
    llmErrors: err.llm || 0,
    agentErrors: err.agent || 0,
    validationErrors: err.validation || 0,
  }
})

const errorRows = computed(() => {
  const s = stats.value
  const total = s.totalErrors || 1
  const items = [
    { type: '请求超时', count: s.timeoutErrors, severity: 'warning', severityLabel: '警告' },
    { type: 'LLM错误', count: s.llmErrors, severity: 'danger', severityLabel: '严重' },
    { type: 'Agent错误/熔断降级', count: s.agentErrors, severity: 'danger', severityLabel: '严重' },
    { type: 'Schema校验失败', count: s.validationErrors, severity: 'info', severityLabel: '提示' },
  ].filter(e => e.count > 0).sort((a, b) => b.count - a.count)
  return items.map(e => ({ ...e, percent: (e.count / total * 100).toFixed(1) }))
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
.data-table td { padding: 12px 16px; font-size: 13px; color: #333; border-bottom: 1px solid #f0f0f0; }
</style>
