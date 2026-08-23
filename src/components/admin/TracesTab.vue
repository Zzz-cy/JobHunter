<template>
  <div>
    <div class="section-header">
      <h2>请求追踪</h2>
      <div class="trace-search">
        <input
          v-model="traceId"
          type="text"
          placeholder="输入Trace ID..."
          class="trace-input"
          @keydown.enter="searchTrace"
        />
        <button class="refresh-btn" @click="searchTrace">🔍 查询</button>
      </div>
    </div>
    <div v-if="traceDetail" class="chart-card">
      <h3>Trace: {{ traceId }}</h3>
      <div class="trace-meta">
        总耗时: {{ traceDetail.total_duration ? traceDetail.total_duration.toFixed(3) : '-' }}s
        | Span数: {{ spans.length }}
        | 状态: <StatusBadge :type="traceDetail.status === 'completed' ? 'success' : 'danger'">{{ traceDetail.status }}</StatusBadge>
      </div>
      <div class="trace-timeline">
        <div
          v-for="(span, i) in spans"
          :key="i"
          class="trace-step"
          :class="{ error: span.status === 'failed' }"
        >
          <div class="step-header">
            <span class="step-name">{{ span.name || span.operation }}</span>
            <span class="step-duration">{{ span.duration ? span.duration.toFixed(3) + 's' : '-' }}</span>
          </div>
          <div class="step-detail">
            状态: <StatusBadge :type="span.status === 'completed' ? 'success' : span.status === 'failed' ? 'danger' : 'info'">{{ span.status }}</StatusBadge>
            <span v-if="span.error_message"><br>错误: {{ span.error_message }}</span>
          </div>
        </div>
        <div v-if="!spans.length" class="empty-state">
          <div class="icon">🔍</div>
          <div class="text">无Span数据</div>
        </div>
      </div>
    </div>
    <div v-else-if="searched" class="empty-state">
      <div class="icon">🔍</div>
      <div class="text">未找到该Trace ID的记录</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'
import { getTraceDetail } from '@/api'

const traceId = ref('')
const traceDetail = ref(null)
const searched = ref(false)

async function searchTrace() {
  if (!traceId.value.trim()) return
  searched.value = true
  try {
    const resp = await getTraceDetail(traceId.value.trim())
    traceDetail.value = resp.data || null
  } catch {
    traceDetail.value = null
  }
}
</script>

<style scoped>
.trace-search {
  display: flex;
  gap: 10px;
  align-items: center;
}

.trace-input {
  padding: 8px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  width: 200px;
  outline: none;
}
.trace-input:focus { border-color: #667eea; }

.chart-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.chart-card h3 { font-size: 15px; color: #333; margin-bottom: 16px; }

.trace-meta {
  margin-bottom: 12px;
  font-size: 13px;
  color: #666;
}

.trace-timeline {
  position: relative;
  padding-left: 30px;
}

.trace-timeline::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e5e7eb;
}

.trace-step {
  position: relative;
  padding: 12px 0;
}

.trace-step::before {
  content: '';
  position: absolute;
  left: -24px;
  top: 16px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #10b981;
  border: 2px solid white;
}

.trace-step.error::before { background: #ef4444; }

.step-header {
  display: flex;
  justify-content: space-between;
}

.step-name { font-size: 14px; font-weight: 600; color: #333; }
.step-duration { font-size: 12px; color: #667eea; font-weight: 500; }
.step-detail { font-size: 12px; color: #999; margin-top: 4px; }
</style>
