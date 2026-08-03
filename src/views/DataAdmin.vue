<template>
  <div class="data-admin-page page-container">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon color="#409eff"><DataAnalysis /></el-icon>
        数据管理
      </h1>
      <p class="page-desc">同步爬虫采集的职位数据到数据库</p>
    </div>

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
            请让爬虫把数据放到后端 <code>backend/db/data/jobs_raw.json</code>
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

    <!-- 导入操作 -->
    <el-card class="action-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon color="#e6a23c"><UploadFilled /></el-icon>
          导入操作
        </div>
      </template>

      <el-alert
        class="action-tip"
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          点击「同步数据」会把上述文件导入数据库。
          已存在的职位会自动跳过,已存在的公司会自动补全缺失字段,可重复点击。
        </template>
      </el-alert>

      <div class="action-row">
        <el-button
          type="primary"
          size="large"
          :loading="importing"
          :disabled="!preview.exists || importing"
          @click="handleImport"
        >
          <el-icon v-if="!importing"><Upload /></el-icon>
          {{ importing ? '导入中...' : '同步爬虫数据' }}
        </el-button>

        <el-button size="large" @click="loadPreview" :disabled="importing">
          查看最新状态
        </el-button>
      </div>

      <!-- 导入状态 -->
      <div class="import-status" v-if="importStatus">
        <el-alert
          :type="importStatus.type"
          :title="importStatus.title"
          :description="importStatus.desc"
          show-icon
          :closable="false"
        />
      </div>
    </el-card>

    <!-- 说明 -->
    <el-card class="tip-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon color="#909399"><InfoFilled /></el-icon>
          工作原理
        </div>
      </template>
      <el-timeline>
        <el-timeline-item type="primary" timestamp="步骤 1">
          <strong>爬虫采集</strong>
          <p>爬虫(独立项目)抓取招聘网站数据,输出 JSON 文件</p>
        </el-timeline-item>
        <el-timeline-item type="success" timestamp="步骤 2">
          <strong>放置文件</strong>
          <p>爬虫把 <code>jobs_raw.json</code> 放到后端 <code>backend/db/data/</code></p>
        </el-timeline-item>
        <el-timeline-item type="warning" timestamp="步骤 3">
          <strong>手动同步</strong>
          <p>点击上方按钮触发导入:公司去重、行业归一化、技能关联、防撞码入库</p>
        </el-timeline-item>
        <el-timeline-item type="danger" timestamp="步骤 4">
          <strong>数据可用</strong>
          <p>导入完成后,职位列表/搜索/推荐即可使用最新数据</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const loadingPreview = ref(false)
const importing = ref(false)
const preview = ref({ exists: false })
const importStatus = ref(null)

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

// 触发导入
const handleImport = async () => {
  importing.value = true
  importStatus.value = null
  try {
    const res = await request.post('/crawl/import')
    ElMessage.success('导入任务已启动,后台执行中(约1分钟)')
    // 后台任务约需 1 分钟,这里立即返回,提示用户等待
    importStatus.value = {
      type: 'warning',
      title: '导入任务已启动',
      desc: '后台正在执行(约1分钟)。完成后可直接去职位列表查看。期间可点击「查看最新状态」刷新。',
    }
    // 60 秒后自动清除"导入中"提示,允许再次操作
    setTimeout(() => {
      importing.value = false
    }, 60000)
  } catch (e) {
    importing.value = false
    importStatus.value = {
      type: 'error',
      title: '导入失败',
      desc: e.message || '请检查后端日志',
    }
  }
}

onMounted(() => {
  loadPreview()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 26px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.page-desc {
  color: #909399;
  font-size: 14px;
}

.preview-card,
.action-card,
.tip-card {
  margin-bottom: 16px;
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
