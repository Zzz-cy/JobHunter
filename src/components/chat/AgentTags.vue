<template>
  <div class="agent-tags">
    <span
      v-for="(task, i) in tasks"
      :key="i"
      class="agent-tag"
      :class="tagClass(task.task_type)"
    >
      {{ tagLabel(task.task_type) }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  tasks: { type: Array, default: () => [] },
})

const TAG_MAP = {
  job_analysis: { cls: 'analysis', label: '📊 分析' },
  skill_gap: { cls: 'analysis', label: '🔍 差距评估' },
  learning_path: { cls: 'plan', label: '🎓 规划' },
  trend_prediction: { cls: 'predict', label: '📈 预测' },
  report_generation: { cls: 'report', label: '📝 报告' },
  job_compare: { cls: 'compare', label: '⚖️ 对比' },
  resume_match: { cls: 'match', label: '🎯 匹配' },
}

function tagClass(type) {
  return TAG_MAP[type]?.cls || 'general'
}

function tagLabel(type) {
  return TAG_MAP[type]?.label || '💬 问答'
}
</script>

<style scoped>
.agent-tags {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.agent-tag {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.analysis { background: #e3f2fd; color: #1565c0; }
.compare  { background: #fff3e0; color: #e65100; }
.plan     { background: #f3e5f5; color: #6a1b9a; }
.predict  { background: #ffebee; color: #c62828; }
.report   { background: #e0f2f1; color: #00695c; }
.match    { background: #e8f5e9; color: #2e7d32; }
.general  { background: #f5f5f5; color: #616161; }
</style>
