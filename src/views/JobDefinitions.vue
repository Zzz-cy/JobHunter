<template>
  <div class="job-def-page page-container">
    <!-- 发现操作(管理员) -->
    <el-card v-if="isAdmin" class="action-card" shadow="never">
      <div class="action-row">
        <el-button
          type="primary"
          size="large"
          :loading="state.running"
          :disabled="state.running"
          @click="handleDiscover"
        >
          <el-icon v-if="!state.running"><MagicStick /></el-icon>
          {{ state.running ? '发现中...' : '开始新岗位发现' }}
        </el-button>
        <span class="header-hint">从飙升技能与近期职位中发现新兴岗位, LLM 基于真实 JD 归纳画像</span>
        <span v-if="state.message" class="state-msg" :class="{ running: state.running }">
          {{ state.message }}
        </span>
      </div>
      <el-alert
        v-if="state.running"
        type="warning"
        :closable="false"
        show-icon
        class="state-tip"
        :title="`第2步逐个生成画像: 成功 ${state.done} / 失败 ${state.failed} / 共 ${state.total}`"
      />
    </el-card>

    <!-- 岗位卡片列表 -->
    <div v-loading="loading">
      <el-empty v-if="!loading && !items.length" description="暂无岗位定义">
        <p class="empty-hint" v-if="isAdmin">点击上方「开始新岗位发现」生成第一批岗位</p>
      </el-empty>

      <el-card v-for="item in items" :key="item.id" class="def-card" shadow="never">
        <template #header>
          <div class="def-header">
            <div class="def-title">
              <span class="def-name">{{ item.name }}</span>
              <el-tag size="small" :type="item.source === 'manual' ? 'warning' : 'primary'">
                {{ item.source === 'manual' ? '人工定义' : 'AI定义' }}
              </el-tag>
              <el-tag size="small" :type="statusType[item.status]">{{ statusText[item.status] }}</el-tag>
              <el-tag v-if="item.version > 1" size="small" type="info" effect="plain">v{{ item.version }}</el-tag>
            </div>
            <div class="def-actions">
              <span class="def-meta">{{ item.job_count }} 条职位证据 · {{ item.updated_at }}</span>
              <el-button
                v-if="isAdmin && item.status !== 'generating'"
                size="small"
                @click="openEdit(item)"
              >
                人工修正
              </el-button>
            </div>
          </div>
        </template>

        <!-- 失败原因 -->
        <el-alert v-if="item.status === 'failed'" type="error" :closable="false" show-icon
                  :title="item.error_msg || '生成失败'" class="def-error" />

        <!-- 生成中骨架 -->
        <div v-if="item.status === 'generating'" class="generating">
          <el-icon class="is-loading"><Loading /></el-icon>
          LLM 正在基于真实 JD 生成画像...
        </div>

        <!-- 画像四要素 -->
        <template v-if="item.status === 'done' && item.definition">
          <div class="def-section">
            <h4>核心职责</h4>
            <ol class="duty-list">
              <li v-for="(d, i) in item.definition.core_duties" :key="i">{{ d }}</li>
            </ol>
          </div>
          <div class="def-section">
            <h4>必备技能</h4>
            <div class="skill-tags">
              <el-tag v-for="(s, i) in item.definition.must_skills" :key="i" type="danger" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
          <div class="def-section" v-if="item.definition.plus_skills?.length">
            <h4>加分技能</h4>
            <div class="skill-tags">
              <el-tag v-for="(s, i) in item.definition.plus_skills" :key="i" type="success" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
          <div class="def-section" v-if="item.definition.industries?.length">
            <h4>主要行业</h4>
            <div class="skill-tags">
              <el-tag v-for="(s, i) in item.definition.industries" :key="i" type="info" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
        </template>

        <!-- 发现依据 -->
        <div class="evidence" v-if="item.evidence_skills?.length">
          <span class="evidence-label">发现依据(飙升技能):</span>
          <el-tag v-for="(s, i) in item.evidence_skills" :key="i" size="small" effect="plain">{{ s }}</el-tag>
        </div>
      </el-card>
    </div>

    <!-- 人工修正弹窗 -->
    <el-dialog v-model="editVisible" :title="`人工修正: ${editForm.name}`" width="640px">
      <el-alert type="info" :closable="false" show-icon class="edit-tip"
                title="每行一条, 保存后标记为人工定义, 之后的重新发现不会覆盖" />
      <el-form label-width="80px">
        <el-form-item label="核心职责">
          <el-input v-model="editForm.core_duties" type="textarea" :rows="5" placeholder="每行一条职责" />
        </el-form-item>
        <el-form-item label="必备技能">
          <el-input v-model="editForm.must_skills" type="textarea" :rows="3" placeholder="每行一个技能" />
        </el-form-item>
        <el-form-item label="加分技能">
          <el-input v-model="editForm.plus_skills" type="textarea" :rows="3" placeholder="每行一个技能" />
        </el-form-item>
        <el-form-item label="主要行业">
          <el-input v-model="editForm.industries" type="textarea" :rows="2" placeholder="每行一个行业" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

const { isAdmin } = storeToRefs(useUserStore())

const loading = ref(false)
const items = ref([])
const state = ref({ running: false, message: '', total: 0, done: 0, failed: 0 })
let timer = null

const statusText = { pending: '待生成', generating: '生成中', done: '已完成', failed: '失败' }
const statusType = { pending: 'info', generating: 'warning', done: 'success', failed: 'danger' }

const loadList = async () => {
  loading.value = true
  try {
    const res = await request.get('/job-definitions')
    items.value = res.items
    state.value = res
    // 发现任务运行中每 5 秒轮询, 结束自动停
    if (timer) clearInterval(timer)
    if (res.running) {
      timer = setInterval(loadList, 5000)
    }
  } catch (e) { /* 拦截器已提示 */ } finally {
    loading.value = false
  }
}

const handleDiscover = async () => {
  try {
    await request.post('/job-definitions/discover')
    ElMessage.success('发现任务已启动(约1-2分钟)')
    if (timer) clearInterval(timer)
    timer = setInterval(loadList, 5000)
  } catch (e) { /* 409 拦截器已提示 */ }
}

// ---------- 人工修正 ----------
const editVisible = ref(false)
const saving = ref(false)
const editForm = ref({
  id: null, name: '', core_duties: '', must_skills: '', plus_skills: '', industries: ''
})

// 数组 ↔ 多行文本
const toText = (arr) => (arr || []).join('\n')
const toList = (text) => text.split('\n').map(s => s.trim()).filter(Boolean)

const openEdit = (item) => {
  const d = item.definition || {}
  editForm.value = {
    id: item.id,
    name: item.name,
    core_duties: toText(d.core_duties),
    must_skills: toText(d.must_skills),
    plus_skills: toText(d.plus_skills),
    industries: toText(d.industries),
  }
  editVisible.value = true
}

const handleSave = async () => {
  const form = editForm.value
  const definition = {
    core_duties: toList(form.core_duties),
    must_skills: toList(form.must_skills),
    plus_skills: toList(form.plus_skills),
    industries: toList(form.industries),
  }
  if (!Object.values(definition).some(arr => arr.length)) {
    ElMessage.warning('至少填写一项内容')
    return
  }
  saving.value = true
  try {
    await request.put(`/job-definitions/${form.id}`, { definition })
    ElMessage.success('已保存为人工定义')
    editVisible.value = false
    loadList()
  } catch (e) { /* 拦截器已提示 */ } finally {
    saving.value = false
  }
}

onMounted(loadList)
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.header-hint {
  font-size: 12px;
  color: #909399;
}

.action-card {
  margin-bottom: 16px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.state-msg {
  font-size: 13px;
  color: #909399;
}

.state-msg.running {
  color: #e6a23c;
}

.state-tip {
  margin-top: 12px;
}

.empty-hint {
  color: #909399;
  font-size: 13px;
}

.def-card {
  margin-bottom: 16px;
}

.def-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.def-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.def-name {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.def-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.def-meta {
  font-size: 12px;
  color: #909399;
}

.def-error {
  margin-bottom: 12px;
}

.generating {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e6a23c;
  font-size: 14px;
  padding: 12px 0;
}

.def-section {
  margin-bottom: 14px;
}

.def-section h4 {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  font-weight: 500;
}

.duty-list {
  margin: 0;
  padding-left: 20px;
  color: #303133;
  font-size: 14px;
  line-height: 1.8;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.evidence {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px dashed #e4e7ed;
}

.evidence-label {
  font-size: 12px;
  color: #909399;
  margin-right: 4px;
}

.edit-tip {
  margin-bottom: 16px;
}
</style>
