<template>
  <span class="badge" :class="type"><slot /></span>
</template>

<script setup>
defineProps({ type: { type: String, default: 'info' } })
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}
.success { background: #d1fae5; color: #065f46; }
.warning { background: #fef3c7; color: #92400e; }
.danger { background: #fee2e2; color: #991b1b; }
.info { background: #dbeafe; color: #1e40af; }
</style>
