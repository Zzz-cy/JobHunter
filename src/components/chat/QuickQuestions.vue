<template>
  <div class="quick-questions">
    <button
      v-for="(q, i) in questions"
      :key="i"
      class="quick-btn"
      @click="$emit('select', q.question)"
    >
      {{ q.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  questions: { type: Array, default: () => [] },
})
defineEmits(['select'])
</script>

<style scoped>
.quick-questions {
  padding: 15px 30px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.quick-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  font-size: 13px;
  color: #495057;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

@media (max-width: 768px) {
  .quick-questions { padding: 10px 20px; }
}
</style>
