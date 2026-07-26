<template>
  <div class="stat-card" :class="type">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: '' },
  value: { type: [String, Number], default: '' },
  sub: { type: String, default: '' },
  type: { type: String, default: '' },
})
</script>

<style scoped>
.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.label {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
}

.value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.sub {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.stat-card.success .value { color: #10b981; }
.stat-card.warning .value { color: #f59e0b; }
.stat-card.danger .value { color: #ef4444; }
.stat-card.info .value { color: #3b82f6; }
</style>
