<template>
  <div class="progress-bar">
    <div
      class="fill"
      :class="colorClass"
      :style="{ width: Math.min(Math.max(value, 0), 100) + '%' }"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  colorClass: { type: String, default: 'green' },
})
</script>

<style scoped>
.progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}
.fill.green { background: #10b981; }
.fill.yellow { background: #f59e0b; }
.fill.red { background: #ef4444; }
</style>
