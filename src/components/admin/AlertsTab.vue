<template>
  <div>
    <div class="section-header">
      <h2>告警规则与历史</h2>
      <button class="refresh-btn" @click="$emit('refresh')">🔄 刷新</button>
    </div>

    <div class="chart-card" style="margin-bottom:20px;">
      <h3>当前告警规则</h3>
      <div class="data-table">
        <table>
          <thead><tr><th>规则名称</th><th>触发条件</th><th>级别</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="(rule, i) in rules" :key="i">
              <td>{{ rule.name }}</td>
              <td>{{ rule.condition }}</td>
              <td><StatusBadge :type="rule.severity">{{ rule.severityLabel }}</StatusBadge></td>
              <td><StatusBadge :type="rule.enabled ? 'success' : 'info'">{{ rule.enabled ? '已启用' : '已禁用' }}</StatusBadge></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="chart-card">
      <h3>最近告警</h3>
      <div v-if="alertList.length" class="alert-list">
        <div
          v-for="(alert, i) in alertList"
          :key="i"
          class="alert-item"
          :class="alert.severity || 'warning'"
        >
          <div class="alert-title">{{ alert.title || alert.name }}</div>
          <div class="alert-desc">{{ alert.description || alert.message }}</div>
          <div class="alert-time">{{ alert.timestamp || alert.created_at || '-' }}</div>
        </div>
      </div>
      <div v-else class="empty-state">
        <div class="icon">✅</div>
        <div class="text">暂无告警记录，系统运行正常</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'

defineEmits(['refresh'])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const rules = [
  { name: '错误率告警', condition: '错误率 > 5%', severity: 'critical', severityLabel: '严重', enabled: true },
  { name: 'P99延迟告警', condition: 'P99延迟 > 30s', severity: 'warning', severityLabel: '警告', enabled: true },
  { name: 'Agent连续失败', condition: '同一Agent连续失败 > 3次', severity: 'critical', severityLabel: '严重', enabled: true },
  { name: 'LLM成本告警', condition: '日成本 > 预算80%', severity: 'warning', severityLabel: '警告', enabled: true },
  { name: '低置信度告警', condition: '意图识别低置信度(<0.6)比例 > 30%', severity: 'info', severityLabel: '提示', enabled: false },
]

const alertList = computed(() => {
  const d = props.data.data || props.data
  return Array.isArray(d) ? d : []
})
</script>

<style scoped>
.chart-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.chart-card h3 { font-size: 15px; color: #333; margin-bottom: 16px; }

.data-table {
  border-radius: 12px;
  overflow: hidden;
}

.data-table table { width: 100%; border-collapse: collapse; }
.data-table th {
  background: #f8f9fa; padding: 12px 16px; text-align: left;
  font-size: 13px; color: #666; font-weight: 600; border-bottom: 1px solid #eee;
}
.data-table td { padding: 12px 16px; font-size: 13px; color: #333; border-bottom: 1px solid #f0f0f0; }

.alert-item {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  border-left: 4px solid;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.alert-item.critical { border-left-color: #ef4444; }
.alert-item.warning { border-left-color: #f59e0b; }
.alert-item.info { border-left-color: #3b82f6; }

.alert-title { font-size: 14px; font-weight: 600; color: #333; }
.alert-desc { font-size: 13px; color: #666; margin-top: 4px; }
.alert-time { font-size: 11px; color: #999; margin-top: 8px; }
</style>
