<template>
  <div class="model-config">
    <div class="section-header">
      <h2>平台默认模型</h2>
      <button class="refresh-btn" @click="load()">🔄 刷新</button>
    </div>

    <!-- 说明 -->
    <div class="mc-note">
      设置后,顾问的<strong>分析/生成/回答类</strong>任务使用所选模型; 意图识别等轻任务仍走廉价路由, 不会因高频调用拉高成本。
      未设置时按各任务默认路由(flash 兜底)。此设置仅管理员可见/可改, 持久化保存。
    </div>

    <el-card shadow="never" class="mc-card">
      <div class="mc-row">
        <div class="mc-label">当前默认模型</div>
        <el-select
          v-model="selectedModel"
          :loading="loading"
          placeholder="选择默认模型"
          filterable
          style="width: 320px"
        >
          <el-option
            v-for="m in available"
            :key="m.name"
            :value="m.name"
            :label="modelLabel(m)"
          >
            <div class="opt-line">
              <span class="opt-name">{{ m.name }}</span>
              <span class="opt-meta">{{ m.tier || '' }}{{ m.cost_per_1k ? ' · ¥' + m.cost_per_1k + '/1k tokens' : '' }}</span>
            </div>
            <div class="opt-desc">{{ m.description || '' }}</div>
          </el-option>
        </el-select>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!selectedModel || selectedModel === current"
          @click="save"
        >
          保存为平台默认
        </el-button>
      </div>

      <div v-if="!available.length && !loading" class="mc-empty">
        未获取到可用模型列表,请确认 llm 服务已启动。也可手动输入模型名后点保存:
        <el-input v-model="manualModel" placeholder="如 glm-4-flash" style="width: 200px; margin: 0 8px;" />
      </div>

      <div class="mc-foot">
        已生效: <code>{{ current || '(未设置)' }}</code>
        <span v-if="savedMsg" class="mc-saved">✓ {{ savedMsg }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post } from '@/utils/request'

const available = ref([])
const current = ref('')
const selectedModel = ref('')
const manualModel = ref('')
const loading = ref(false)
const saving = ref(false)
const savedMsg = ref('')

function modelLabel(m) {
  const tier = m.tier ? `(${m.tier})` : ''
  const cost = m.cost_per_1k ? ` ¥${m.cost_per_1k}/1k` : ''
  return `${m.name} ${tier}${cost}`
}

async function load() {
  loading.value = true
  try {
    const data = await get('/agents/models')
    available.value = (data && data.available) || []
    // current = 管理员设过的默认(admin_default); 接口同时给 current/admin_default
    const cur = (data && (data.admin_default || data.current)) || ''
    current.value = cur
    // 下拉默认选中: 当前值在可选列表里就选中它; 否则留空让管理员挑
    selectedModel.value = available.value.some((m) => m.name === cur) ? cur : ''
    savedMsg.value = ''
  } catch (err) {
    ElMessage.error((err && err.message) || '加载模型列表失败')
  } finally {
    loading.value = false
  }
}

async function save() {
  const model = selectedModel.value || manualModel.value.trim()
  if (!model) {
    ElMessage.warning('请选择要设为默认的模型')
    return
  }
  saving.value = true
  try {
    const data = await post('/agents/models/default', { model })
    current.value = data.default_model || model
    selectedModel.value = current.value
    savedMsg.value = `已设为平台默认(${current.value})`
    ElMessage.success(`已设置默认模型: ${current.value}`)
  } catch (err) {
    // 403/400/500 提示已由拦截器统一弹出
    const msg = (err && err.message) || '设置失败'
    if (!msg.includes('403')) ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-header h2 { font-size: 18px; color: #303133; }

.refresh-btn {
  padding: 6px 14px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  color: #606266;
}
.refresh-btn:hover { border-color: #667eea; color: #667eea; }

.mc-note {
  background: #f0f4ff;
  border: 1px solid #dbe3ff;
  color: #44527a;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.7;
  margin-bottom: 16px;
}

.mc-card { margin-bottom: 12px; }

.mc-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.mc-label { font-size: 14px; color: #303133; font-weight: 600; }

.opt-line { display: flex; justify-content: space-between; gap: 10px; }
.opt-name { font-weight: 600; }
.opt-meta { color: #667eea; font-size: 12px; }
.opt-desc { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 2px; }

.mc-empty { margin-top: 14px; color: #909399; font-size: 13px; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.mc-foot { margin-top: 14px; font-size: 13px; color: #606266; }
.mc-foot code { background: #f2f3f5; padding: 2px 8px; border-radius: 6px; color: #667eea; }
.mc-saved { color: #34c77b; margin-left: 10px; }
</style>
