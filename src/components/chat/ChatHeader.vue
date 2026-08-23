<template>
  <div class="header">
    <div class="header-left">
      <div class="logo">🎯</div>
      <div>
        <div class="header-title">AI 求职顾问</div>
        <div class="header-subtitle">智能职业咨询 · Agent 驱动</div>
      </div>
    </div>
    <div class="header-right">
      <select class="role-select" :value="role" @change="$emit('update:role', $event.target.value)">
        <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <select class="industry-select" :value="industry" @change="$emit('update:industry', $event.target.value)">
        <option v-for="opt in industryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <div class="status-badge">
        <div class="status-dot"></div>
        <span>{{ modelStatus }}</span>
      </div>
      <router-link to="/admin" class="admin-link">📊</router-link>
    </div>
  </div>
</template>

<script setup>
import { ROLE_OPTIONS, INDUSTRY_OPTIONS } from '@/composables/useChat'

defineProps({
  modelStatus: { type: String, default: '加载中...' },
  role: { type: String, default: 'job_seeker' },
  industry: { type: String, default: 'it' },
})

defineEmits(['update:role', 'update:industry'])

const roleOptions = ROLE_OPTIONS
const industryOptions = INDUSTRY_OPTIONS
</script>

<style scoped>
.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logo {
  width: 45px;
  height: 45px;
  background: white;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.header-title {
  font-size: 20px;
  font-weight: 600;
}

.header-subtitle {
  font-size: 13px;
  opacity: 0.8;
  margin-top: 3px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-select,
.industry-select {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 20px;
  color: white;
  font-size: 13px;
  cursor: pointer;
  outline: none;
}

.role-select option,
.industry-select option {
  color: #333;
  background: white;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  font-size: 13px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4ade80;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.admin-link {
  color: white;
  text-decoration: none;
  font-size: 20px;
  opacity: 0.8;
  transition: opacity 0.2s;
}
.admin-link:hover { opacity: 1; }

@media (max-width: 768px) {
  .header { padding: 15px 20px; }
  .header-title { font-size: 16px; }
}
</style>
