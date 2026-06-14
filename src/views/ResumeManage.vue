<template>
  <div class="resume-page page-container">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon color="#409eff"><Document /></el-icon>
        我的简历
      </h1>
      <p class="page-desc">上传简历文件,AI 自动解析技能档案,用于智能推荐</p>
    </div>

    <el-row :gutter="20">
      <!-- 左侧:简历列表 -->
      <el-col :span="16">
        <!-- 上传区域 -->
        <el-card class="upload-card" shadow="never">
          <el-upload
            ref="uploadRef"
            class="resume-uploader"
            drag
            action="#"
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            :file-list="fileList"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              拖拽文件到此处,或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="upload-tip">
                支持 PDF / Word / 图片格式,单文件不超过 10MB
              </div>
            </template>
          </el-upload>

          <div class="upload-actions" v-if="pendingFile">
            <el-tag type="info" effect="plain">
              {{ pendingFile.name }} ({{ formatSize(pendingFile.size) }})
            </el-tag>
            <el-input
              v-model="resumeTitle"
              placeholder="为这份简历起个名字(如:高级 Python 工程师版)"
              style="flex: 1"
            />
            <el-button
              type="primary"
              :loading="uploading"
              @click="doUpload"
            >
              {{ uploading ? '上传解析中...' : '开始上传解析' }}
            </el-button>
          </div>

          <!-- 解析进度 -->
          <div class="parse-progress" v-if="uploading || parseStatus !== 'idle'">
            <el-steps :active="currentStep" align-center>
              <el-step title="上传文件" :status="stepStatus(0)" />
              <el-step title="OCR 识别" :status="stepStatus(1)" />
              <el-step title="NER 抽取" :status="stepStatus(2)" />
              <el-step title="技能归一" :status="stepStatus(3)" />
            </el-steps>
            <el-alert
              v-if="parseError"
              type="error"
              :title="parseError"
              show-icon
              :closable="false"
              class="parse-error"
            />
          </div>
        </el-card>

        <!-- 简历列表 -->
        <el-card class="list-card" shadow="never">
          <template #header>
            <div class="card-title">
              <span>已上传简历 ({{ resumeList.length }})</span>
              <el-button text @click="refreshList">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>

          <el-empty v-if="!resumeList.length" description="还没有简历,上传一份开始体验智能推荐" />

          <div v-else class="resume-list">
            <div
              v-for="r in resumeList"
              :key="r.id"
              class="resume-item"
            >
              <div class="resume-icon">
                <el-icon :size="32" :color="fileIconColor(r.source_type)">
                  <component :is="fileIcon(r.source_type)" />
                </el-icon>
              </div>
              <div class="resume-info">
                <div class="resume-name">
                  {{ r.title || `简历 #${r.id}` }}
                  <el-tag size="small" :type="statusTagType(r.parse_status)">
                    {{ statusText(r.parse_status) }}
                  </el-tag>
                  <el-tag v-if="r.is_primary" size="small" type="success">默认</el-tag>
                </div>
                <div class="resume-meta">
                  {{ r.work_years ? `${r.work_years}年经验` : '经验未知' }}
                  · {{ r.education || '学历未知' }}
                  · {{ formatTime(r.created_at) }}
                </div>
                <!-- 解析出来的技能标签 -->
                <div class="resume-skills" v-if="r.skills && r.skills.length">
                  <SkillTag
                    v-for="s in r.skills.slice(0, 10)"
                    :key="s.id"
                    :skill="s"
                    size="small"
                  />
                  <span v-if="r.skills.length > 10" class="more-skills">
                    +{{ r.skills.length - 10 }}
                  </span>
                </div>
              </div>
              <div class="resume-actions">
                <el-button size="small" @click="viewDetail(r)">查看</el-button>
                <el-button size="small" type="primary" @click="useForRecommend(r)">
                  用于推荐
                </el-button>
                <el-dropdown @command="(cmd) => handleCommand(cmd, r)">
                  <el-button size="small" text>
                    <el-icon><More /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="setPrimary" v-if="!r.is_primary">
                        设为默认
                      </el-dropdown-item>
                      <el-dropdown-item command="reparse">重新解析</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <span style="color: #f56c6c">删除</span>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧:提示 -->
      <el-col :span="8">
        <el-card class="tip-card" shadow="never">
          <template #header>
            <div class="card-title">
              <el-icon color="#e6a23c"><InfoFilled /></el-icon>
              解析说明
            </div>
          </template>
          <el-timeline>
            <el-timeline-item type="primary" timestamp="步骤 1">
              <strong>文件上传</strong>
              <p>支持 PDF / Word / 图片,文件会被安全存储</p>
            </el-timeline-item>
            <el-timeline-item type="success" timestamp="步骤 2">
              <strong>OCR 文字识别</strong>
              <p>讯飞文档解析 API 识别图片和扫描件中的文字</p>
            </el-timeline-item>
            <el-timeline-item type="warning" timestamp="步骤 3">
              <strong>NER 字段抽取</strong>
              <p>HanLP + 自定义模型抽取工作经历、教育、技能等结构化字段</p>
            </el-timeline-item>
            <el-timeline-item type="danger" timestamp="步骤 4">
              <strong>大模型语义理解</strong>
              <p>讯飞星火做复杂语义分析,识别技能熟练度、年限</p>
            </el-timeline-item>
            <el-timeline-item type="info" timestamp="步骤 5">
              <strong>技能归一化</strong>
              <p>把抽取的技能 mention 映射到技能字典的标准 ID</p>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <el-card class="tip-card" shadow="never">
          <template #header>
            <div class="card-title">
              <el-icon color="#409eff"><Key /></el-icon>
              使用提示
            </div>
          </template>
          <ul class="tip-list">
            <li>建议上传 PDF 格式,解析效果最佳</li>
            <li>可上传多份简历对应不同岗位方向</li>
            <li>设为默认的简历将用于首页推荐</li>
            <li>解析失败可重新解析,不会重复计费</li>
            <li>文件加密存储,仅你本人可见</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import SkillTag from '@/components/common/SkillTag.vue'
// import { useResumeStore } from '@/stores/resume'

const router = useRouter()
// const resumeStore = useResumeStore()

const uploadRef = ref(null)
const fileList = ref([])
const pendingFile = ref(null)
const resumeTitle = ref('')
const uploading = ref(false)
const parseStatus = ref('idle')
const parseError = ref('')
const resumeList = ref([])

const currentStep = computed(() => {
  const map = { idle: 0, uploading: 0, parsing: 2, done: 4, failed: 4 }
  return map[parseStatus.value] ?? 0
})

const stepStatus = (idx) => {
  if (parseStatus.value === 'failed') {
    return idx < currentStep.value ? 'success' : idx === currentStep.value ? 'error' : 'wait'
  }
  if (idx < currentStep.value) return 'success'
  if (idx === currentStep.value && parseStatus.value !== 'idle') return 'process'
  return 'wait'
}

const handleFileChange = (file) => {
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 10MB')
    fileList.value = []
    return
  }
  pendingFile.value = file.raw
  if (!resumeTitle.value) {
    const name = file.name.replace(/\.[^.]+$/, '')
    resumeTitle.value = name
  }
}

const handleExceed = () => {
  ElMessage.warning('一次只能上传一个文件,请先移除当前文件')
}

const doUpload = async () => {
  if (!pendingFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  parseStatus.value = 'uploading'
  parseError.value = ''
  // TODO: 调用 store 上传 + 轮询
  // try {
  //   await resumeStore.uploadResume(pendingFile.value)
  //   parseStatus.value = resumeStore.uploadStatus
  //   if (parseStatus.value === 'done') {
  //     ElMessage.success('简历解析完成')
  //     await refreshList()
  //     resetUpload()
  //   } else if (parseStatus.value === 'failed') {
  //     parseError.value = resumeStore.parseError
  //   }
  // } finally {
  //   uploading.value = false
  // }
  console.log('[TODO] doUpload', pendingFile.value.name, resumeTitle.value)
  setTimeout(() => {
    uploading.value = false
    parseStatus.value = 'idle'
  }, 500)
}

const resetUpload = () => {
  pendingFile.value = null
  resumeTitle.value = ''
  fileList.value = []
  parseStatus.value = 'idle'
  uploadRef.value?.clearFiles()
}

const refreshList = async () => {
  // TODO: 加载简历列表
  // await resumeStore.fetchResumeList()
  // resumeList.value = resumeStore.resumeList
  console.log('[TODO] refreshList')
}

const viewDetail = (r) => {
  // TODO: 打开简历详情抽屉/弹窗
  ElMessage.info(`查看简历 ${r.id}(待实现)`)
}

const useForRecommend = (r) => {
  router.push({ path: '/recommend', query: { resumeId: r.id } })
}

const handleCommand = async (cmd, r) => {
  if (cmd === 'setPrimary') {
    // TODO: 设为默认简历
    // await request.put(`/resumes/${r.id}/primary`)
    ElMessage.success('已设为默认简历')
    await refreshList()
  } else if (cmd === 'reparse') {
    // TODO: 重新解析
    // await request.post(`/resumes/${r.id}/reparse`)
    ElMessage.success('已提交重新解析')
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除这份简历吗?删除后无法恢复', '提示', {
        type: 'warning'
      })
      // TODO: 删除简历
      // await request.delete(`/resumes/${r.id}`)
      ElMessage.success('已删除')
      await refreshList()
    } catch {}
  }
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatTime = (t) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

const statusText = (s) => ({
  pending: '等待解析',
  parsing: '解析中',
  done: '已解析',
  failed: '解析失败'
}[s] || s)

const statusTagType = (s) => ({
  pending: 'info',
  parsing: 'warning',
  done: 'success',
  failed: 'danger'
}[s] || 'info')

const fileIcon = (type) => ({
  pdf: 'Document',
  image: 'Picture',
  word: 'Files',
  manual: 'Edit'
}[type] || 'Document')

const fileIconColor = (type) => ({
  pdf: '#f56c6c',
  image: '#409eff',
  word: '#409eff',
  manual: '#909399'
}[type] || '#909399')

// TODO: 初始化加载
// import { onMounted } from 'vue'
// onMounted(() => {
//   refreshList()
// })
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

.upload-card,
.list-card,
.tip-card {
  margin-bottom: 16px;
}

.resume-uploader {
  width: 100%;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}

.upload-text {
  color: #606266;
  font-size: 14px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}

.upload-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #ebeef5;
}

.parse-progress {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #ebeef5;
}

.parse-error {
  margin-top: 12px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.resume-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resume-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  transition: all 0.2s;
}

.resume-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.resume-icon {
  flex: 0 0 40px;
}

.resume-info {
  flex: 1;
  min-width: 0;
}

.resume-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.resume-meta {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}

.resume-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.more-skills {
  font-size: 12px;
  color: #909399;
  align-self: center;
}

.resume-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tip-list {
  padding-left: 20px;
  margin: 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.8;
}
</style>
