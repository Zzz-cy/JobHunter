<template>
  <div class="thinking-process">
    <div style="font-weight:600; margin-bottom:8px;">🧠 思考过程</div>
    <div class="thinking-step">
      <span class="step-icon completed">✓</span>
      <span>意图识别：{{ intent.intent }} (置信度: {{ (intent.confidence || 0).toFixed(2) }})</span>
    </div>
    <div class="thinking-step">
      <span class="step-icon completed">✓</span>
      <span>任务分解：{{ tasks.length }} 个子任务</span>
    </div>
    <div class="thinking-step">
      <span class="step-icon completed">✓</span>
      <span>执行完成</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  intent: { type: Object, default: () => ({}) },
  tasks: { type: Array, default: () => [] },
})
</script>

<style scoped>
.thinking-process {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 15px;
  margin-top: 10px;
  font-size: 13px;
  color: #6c757d;
}

.thinking-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px dashed #dee2e6;
}

.thinking-step:last-child { border-bottom: none; }

.step-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex-shrink: 0;
}

.step-icon.completed {
  background: #4ade80;
  color: white;
}
</style>
