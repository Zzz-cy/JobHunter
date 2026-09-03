<template>
  <div class="admin-layout">
    <div class="main-content">
      <!-- Tab切换 -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 请求概览 -->
      <div v-show="activeTab === 'overview'" class="tab-panel">
        <OverviewTab :data="metricsData" />
      </div>

      <!-- Agent看板 -->
      <div v-show="activeTab === 'agents'" class="tab-panel">
        <AgentsTab :data="metricsData" @refresh="loadData" />
      </div>

      <!-- LLM看板 -->
      <div v-show="activeTab === 'llm'" class="tab-panel">
        <LLMTab :data="metricsData" @refresh="loadData" />
      </div>

      <!-- 平台默认模型配置 -->
      <div v-show="activeTab === 'modelcfg'" class="tab-panel">
        <ModelConfig />
      </div>

      <!-- 意图分布 -->
      <div v-show="activeTab === 'intents'" class="tab-panel">
        <IntentsTab :data="metricsData" @refresh="loadData" />
      </div>

      <!-- 错误分析 -->
      <div v-show="activeTab === 'errors'" class="tab-panel">
        <ErrorsTab :data="metricsData" @refresh="loadData" />
      </div>

      <!-- 追踪详情 -->
      <div v-show="activeTab === 'traces'" class="tab-panel">
        <TracesTab :data="metricsData" @refresh="loadData" />
      </div>

      <!-- 告警规则 -->
      <div v-show="activeTab === 'alerts'" class="tab-panel">
        <AlertsTab :data="alertData" @refresh="loadData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import '@/styles/chat.css'
import { ref, onMounted } from 'vue'
import { get } from '@/utils/request'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import OverviewTab from '@/components/admin/OverviewTab.vue'
import AgentsTab from '@/components/admin/AgentsTab.vue'
import LLMTab from '@/components/admin/LLMTab.vue'
import ModelConfig from '@/components/admin/ModelConfig.vue'
import IntentsTab from '@/components/admin/IntentsTab.vue'
import ErrorsTab from '@/components/admin/ErrorsTab.vue'
import TracesTab from '@/components/admin/TracesTab.vue'
import AlertsTab from '@/components/admin/AlertsTab.vue'

const tabs = [
  { id: 'overview', label: '请求概览' },
  { id: 'agents', label: 'Agent看板' },
  { id: 'llm', label: 'LLM看板' },
  { id: 'modelcfg', label: '模型配置' },
  { id: 'intents', label: '意图分布' },
  { id: 'errors', label: '错误分析' },
  { id: 'traces', label: '追踪详情' },
  { id: 'alerts', label: '告警规则' },
]

const activeTab = ref('overview')
const metricsData = ref({})
const alertData = ref({})

const autoRefreshTabs = ['overview', 'agents', 'llm']

async function loadData() {
  try {
    const m = await get('/v1/admin/metrics')
    if (m) metricsData.value = m
  } catch {}
  try {
    const a = await get('/v1/admin/alerts')
    if (a) alertData.value = a
  } catch {}
}

const { start, stop } = useAutoRefresh(() => {
  if (autoRefreshTabs.includes(activeTab.value)) {
    loadData()
  }
}, 30000)

function switchTab(tabId) {
  activeTab.value = tabId
  loadData()
}

onMounted(() => {
  loadData()
  start()
})
</script>

<style scoped>
.admin-layout {
  background: #f0f2f5;
  min-height: 100vh;
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 30px;
}

.tab-bar {
  display: flex;
  gap: 0;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.tab-btn {
  padding: 14px 24px;
  border: none;
  background: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
  font-weight: 500;
}

.tab-btn:hover { background: #f8f9fa; }

.tab-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

@media (max-width: 768px) {
  .main-content { padding: 10px 15px; }
  .tab-btn { padding: 10px 14px; font-size: 12px; }
}
</style>
