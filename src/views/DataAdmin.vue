<template>
  <div class="data-admin-page page-container">
    <!-- 数据文件预览 -->
    <el-card class="preview-card" shadow="never" v-loading="loadingPreview">
      <template #header>
        <div class="card-title">
          <span>待导入数据文件</span>
          <el-button text @click="loadPreview">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <div v-if="!preview.exists" class="empty-state">
        <el-empty description="数据文件不存在">
          <p class="empty-hint">
            请让爬虫把数据放到 <code>db/data/jobs_raw.json</code>
          </p>
        </el-empty>
      </div>

      <div v-else class="preview-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件名">{{ preview.file_name }}</el-descriptions-item>
          <el-descriptions-item label="批次号">{{ preview.crawl_batch || '-' }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ preview.file_size_mb }} MB</el-descriptions-item>
          <el-descriptions-item label="最后修改">{{ preview.last_modified }}</el-descriptions-item>
          <el-descriptions-item label="职位总数">
            <el-tag type="primary">{{ preview.total }} 条</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="字段填充">
            <el-tag size="small">官网 {{ preview.website_filled }}</el-tag>
            <el-tag size="small" type="success">行业 {{ preview.industry_filled }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <!-- 同步操作 -->
    <el-card class="action-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon color="#e6a23c"><UploadFilled /></el-icon>
          同步操作
        </div>
      </template>

      <el-alert
        class="action-tip"
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          点击「一键同步所有库」依次完成: MySQL 导入 → ES 同步 → 向量库 → 知识图谱。
          某个库未启动只标记该步失败, 不影响其他库。
        </template>
      </el-alert>

      <div class="action-row">
        <el-button
          type="success"
          size="large"
          :loading="syncAll.running"
          :disabled="!preview.exists || syncAll.running"
          @click="handleSyncAll"
        >
          <el-icon v-if="!syncAll.running"><MagicStick /></el-icon>
          {{ syncAll.running ? '全库同步中...' : '一键同步所有库' }}
        </el-button>

        <el-button size="large" @click="loadPreview" :disabled="syncAll.running">
          查看最新状态
        </el-button>
      </div>

      <!-- 四库同步进度 -->
      <div class="sync-steps" v-if="syncAll.steps && syncAll.steps.length">
        <div v-for="s in syncAll.steps" :key="s.key" class="sync-step-item">
          <el-tag
            size="small"
            :type="{ pending: 'info', running: 'warning', done: 'success', failed: 'danger' }[s.status]"
          >
            {{ { pending: '待开始', running: '进行中', done: '完成', failed: '失败' }[s.status] }}
          </el-tag>
          <span class="step-name">{{ s.name }}</span>
          <span class="step-msg" :class="s.status">{{ s.message }}</span>
        </div>
        <el-alert
          v-if="syncAll.message"
          :type="syncAll.running ? 'warning' : 'success'"
          :title="syncAll.message"
          show-icon
          :closable="false"
          class="sync-summary"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const loadingPreview = ref(false)
const preview = ref({ exists: false })

// ---------- 一键全库同步 ----------
const syncAll = ref({ running: false, steps: [] })
let syncTimer = null

const loadSyncStatus = async () => {
  try {
    const res = await request.get('/crawl/sync-status')
    syncAll.value = res
    // 运行中每 5 秒轮询, 结束自动停
    if (syncTimer) clearInterval(syncTimer)
    if (res.running) {
      syncTimer = setInterval(loadSyncStatus, 5000)
    }
  } catch (e) { /* 静默 */ }
}

const handleSyncAll = async () => {
  try {
    const res = await request.post('/crawl/sync-all')
    ElMessage.success('全库同步已启动(约2-5分钟)')
    syncAll.value = res
    if (syncTimer) clearInterval(syncTimer)
    syncTimer = setInterval(loadSyncStatus, 5000)
  } catch (e) { /* 409/404 拦截器已提示 */ }
}

onBeforeUnmount(() => {
  if (syncTimer) clearInterval(syncTimer)
})

// 加载文件预览
const loadPreview = async () => {
  loadingPreview.value = true
  try {
    const res = await request.get('/crawl/preview')
    preview.value = res
  } catch (e) {
    // 接口失败时保持空状态
  } finally {
    loadingPreview.value = false
  }
}

onMounted(() => {
  loadPreview()
  loadSyncStatus()   // 刷新页面也能看到进行中的同步进度
})
</script>

<style scoped>
.preview-card,
.action-card,
.tip-card {
  margin-bottom: 16px;
}

.sync-steps {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
}

.sync-step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.step-name {
  font-weight: 500;
  color: #303133;
  min-width: 100px;
}

.step-msg {
  color: #909399;
  font-size: 12px;
}

.step-msg.failed {
  color: #f56c6c;
}

.sync-summary {
  margin-top: 8px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.empty-state {
  padding: 20px 0;
}

.empty-hint {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

.empty-hint code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #e6a23c;
}

.action-tip {
  margin-bottom: 16px;
}

.action-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.import-status {
  margin-top: 8px;
}

.preview-info code,
.tip-card code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #409eff;
  font-size: 13px;
}
</style>
