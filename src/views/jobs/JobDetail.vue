<template>
  <div class="job-detail-page" v-loading="loading">
    <!-- 顶部:职位基本信息 -->
    <div class="job-header">
      <div class="page-container">
        <el-breadcrumb separator="/" class="breadcrumb">
          <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item :to="{ path: '/jobs' }">职位列表</el-breadcrumb-item>
          <el-breadcrumb-item>{{ job.title || '职位详情' }}</el-breadcrumb-item>
        </el-breadcrumb>

        <div class="job-main">
          <div class="job-info">
            <h1 class="job-title">{{ job.title }}</h1>
            <div class="job-salary">{{ formatSalary(job) }}</div>

            <div class="job-meta">
              <span class="meta-item"><el-icon><Location /></el-icon> {{ job.city }}</span>
              <span class="meta-item"><el-icon><Briefcase /></el-icon> {{ job.experience_req }}</span>
              <span class="meta-item"><el-icon><Reading /></el-icon> {{ job.education_req }}</span>
              <span class="meta-item" v-if="job.job_type">
                <el-icon><Clock /></el-icon> {{ jobTypeText }}
              </span>
            </div>
          </div>

          <div class="job-actions">
            <!-- 从 AI 顾问卡片跳进来时, 提供"返回 AI 顾问": 顾问会话状态是模块级单例, 返回后原对话/卡片仍在 -->
            <el-button v-if="fromConsultant" type="primary" plain size="large" @click="backToConsultant">
              <el-icon style="vertical-align: -2px;"><Back /></el-icon>
              <span style="margin-left: 4px;">返回 AI 顾问</span>
            </el-button>

            <!-- 问顾问: 跳 AI 求职顾问并自动带该岗位上下文, 让顾问针对这条 JD 分析匹配度 -->
            <el-button type="warning" size="large" @click="askConsultant">
              <el-icon style="vertical-align: -2px;"><ChatDotRound /></el-icon>
              <span style="margin-left: 4px;">问顾问</span>
            </el-button>

            <el-button
              :type="isFavorited ? 'warning' : 'default'"
              size="large"
              @click="toggleFavorite"
            >
              <el-icon><Star v-if="!isFavorited" /><StarFilled v-else /></el-icon>
              {{ isFavorited ? '已收藏' : '收藏' }}
            </el-button>

            <!-- 切换投递状态:没投→标记已投递;已投→取消投递(再点一次) -->
            <el-button
              :type="hasApplied ? 'success' : 'primary'"
              size="large"
              :loading="submitting"
              @click="markApplied"
            >
              <el-icon><CircleCheck /></el-icon>
              {{ hasApplied ? '已投递(点击取消)' : '标记已投递' }}
            </el-button>

            <!-- 去外站:只跳转,不记录投递(用户点了不一定真投) -->
            <el-button size="large" @click="goExternalApply">
              <el-icon><Link /></el-icon>
              去投递
            </el-button>
          </div>
        </div>

        <!-- 来源标签 -->
        <div class="source-info">
          <el-tag :type="sourceTagType" size="small">{{ sourceText }}</el-tag>
          <span class="publish-time" v-if="job.publish_at">
            发布于 {{ formatDate(job.publish_at) }}
          </span>
        </div>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="page-container detail-body">
      <el-row :gutter="20">
        <!-- 左侧:职位详情 -->
        <el-col :span="17">
          <!-- JD 描述 -->
          <el-card class="detail-card" shadow="never">
            <template #header>
              <div class="card-title">
                <el-icon><Document /></el-icon>
                职位描述
              </div>
            </template>
            <div class="jd-content" v-html="formattedDescription">
            </div>
          </el-card>

          <!-- 技能要求 -->
          <el-card class="detail-card" shadow="never" v-if="job.skills && job.skills.length">
            <template #header>
              <div class="card-title">
                <el-icon><Cpu /></el-icon>
                技能要求
              </div>
            </template>
            <div class="skill-list">
              <SkillTag
                v-for="skill in job.skills"
                :key="skill.skill_id || skill.skill_name"
                :skill="skill"
                @click="searchBySkill"
              />
            </div>
          </el-card>

          <!-- 岗位亮点 -->
          <el-card class="detail-card" shadow="never" v-if="job.advantage">
            <template #header>
              <div class="card-title">
                <el-icon><Trophy /></el-icon>
                岗位亮点
              </div>
            </template>
            <div class="advantage-content">{{ job.advantage }}</div>
          </el-card>
        </el-col>

        <!-- 右侧:公司信息 -->
        <el-col :span="7">
          <el-card class="company-card" shadow="never">
            <template #header>
              <div class="card-title">
                <el-icon><OfficeBuilding /></el-icon>
                公司信息
              </div>
            </template>
            <div class="company-block">
              <el-avatar :size="56" :src="job.company?.logo_url">
                {{ (job.company?.name || '?').charAt(0) }}
              </el-avatar>
              <div class="company-name-block">
                <div class="company-name">{{ job.company?.name || '公司名称未知' }}</div>
                <div class="company-stage">{{ job.company?.stage || '融资阶段未知' }}</div>
              </div>
            </div>

            <el-descriptions :column="1" class="company-desc">
              <el-descriptions-item label="行业">
                {{ job.company?.industry_name || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="规模">
                {{ job.company?.size || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="城市">
                {{ job.company?.city || job.city || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="官网" v-if="job.company?.website">
                <a :href="job.company.website" target="_blank" rel="noopener">
                  {{ job.company.website }}
                </a>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 福利标签 -->
            <div class="welfare-tags" v-if="job.company?.welfare && job.company.welfare.length">
              <el-tag
                v-for="w in job.company.welfare"
                :key="w"
                size="small"
                type="info"
                effect="plain"
              >
                {{ w }}
              </el-tag>
            </div>
          </el-card>

          <!-- 相似职位推荐 -->
          <el-card class="similar-card" shadow="never">
            <template #header>
              <div class="card-title">
                <el-icon><Connection /></el-icon>
                相似职位
              </div>
            </template>
            <div class="similar-empty" v-if="!similarJobs.length">
              <el-empty :image-size="60" description="暂无相似职位" />
            </div>
            <div v-else class="similar-list">
              <div
                v-for="sj in similarJobs"
                :key="sj.id"
                class="similar-item"
                @click="goSimilar(sj)"
              >
                <div class="similar-title">{{ sj.title }}</div>
                <div class="similar-meta">
                  {{ formatSalary(sj) }} · {{ sj.company?.name || '公司未知' }}
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 投递提示 -->
      <el-alert
        type="warning"
        :closable="false"
        class="apply-tip"
        show-icon
      >
        <template #title>
          <strong>温馨提示:</strong>
          本站不提供直接投递,点击「去原网站投递」可跳转至 {{ sourceText }} 完成应聘。
        </template>
      </el-alert>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import SkillTag from '@/components/common/SkillTag.vue'
import { useJobStore } from '@/stores/job'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()

const loading = ref(false)
const job = ref({})
const similarJobs = ref([])
const isFavorited = ref(false)
const hasApplied = ref(false)   // 是否已投递(求职进度里有这条记录)
const submitting = ref(false)   // 标记投递按钮的 loading


// JD 正文排版处理
const formattedDescription = computed(() => {
  let text = job.value.description || job.value.description_text || ''
  if (!text) return '暂无描述'
  // 判断是不是 HTML 格式(包含 <p> <br> <div> 等标签)
  const isHtml = /<[a-z][\s\S]*?>/i.test(text)
  // 公用:小标题加粗
  const boldHeadings = (t) => t.replace(
    /(岗位职责|工作职责|工作内容|职位描述|职责描述|任职要求|职位要求|岗位要求|任职资格|加分项|福利待遇)/g,
    '<strong>$1</strong>'
  )
  if (isHtml) {
    // ---- HTML 格式:信任爬虫数据,解析标签 ----
    text = text.replace(/\r\n/g, ' ').replace(/\n/g, ' ')  // HTML 里换行无意义
    text = text.replace(/<\/p>/gi, '</p>\n')                // </p> 后补换行
    text = text.replace(/<br\s*\/?>/gi, '<br>')             // <br> 统一
    return boldHeadings(text)
  }
  // ---- 纯文本/字面 \n 格式 ----
  text = text.replace(/\\n/g, '\n')      // 字面 \n 转真换行
  text = text.replace(/\r\n/g, '\n')     // 统一 \r\n
  text = text.replace(/\n/g, '<br>')     // 真换行转 <br>
  return boldHeadings(text)
})

const jobTypeText = computed(() => {
  const map = { full: '全职', part: '兼职', intern: '实习' }
  return map[job.value.job_type] || job.value.job_type
})

const sourceText = computed(() => {
  const map = { boss: 'Boss直聘', liepin: '猎聘', official: '官方' }
  return map[job.value.source] || job.value.source || ''
})

const sourceTagType = computed(() => {
  const map = { boss: 'success', liepin: 'warning', official: 'info' }
  return map[job.value.source] || 'info'
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const toggleFavorite = async () => {
  await jobStore.toggleFavorite(route.params.id)
  // route.params.id 是字符串, isFavorited 内部用 Set.has 比较, 必须转 Number
  isFavorited.value = jobStore.isFavorited(Number(route.params.id))
  ElMessage.success(isFavorited.value ? '已收藏' : '已取消收藏')
}

const goExternalApply = async () => {
  if (!job.value.source_url) {
    ElMessage.warning('未找到原站链接')
    return
  }
  ElMessage.info('即将跳转到原网站...')
  window.open(job.value.source_url, '_blank', 'noopener')
}

// 问顾问: 跳到 AI 顾问页(/recommend)并带当前岗位 id, 由 ChatView 自动发起带 context 的咨询
// 未登录会先被路由守卫送到登录页, 登录后带 redirect 跳回并自动发起
const askConsultant = () => {
  router.push({ path: '/recommend', query: { job: route.params.id } })
}

// 从 AI 顾问的岗位卡片跳进来(?from=consultant)才显示"返回 AI 顾问";
// 顾问会话状态模块级保留, 直接回 /recommend 即可接着原对话看卡片
const fromConsultant = computed(() => route.query.from === 'consultant')

const backToConsultant = () => {
  router.push('/recommend')
}

// 切换投递状态:没投 → 标记已投递;已投 → 取消投递
// 用户实际确认投递了才点"标记"(跟"去外站"独立,点了去外站不一定真投)
// 已经标记但想取消(比如误点/放弃投递)→ 再点一次取消
const markApplied = async () => {
  if (submitting.value) return
  submitting.value = true
  const id = Number(route.params.id)
  try {
    if (!hasApplied.value) {
      // 当前没投 → 标记已投递
      await request.post(`/jobs/applications/${id}/submit`)
      jobStore.appliedIds.add(id)
      hasApplied.value = true
      ElMessage.success('已记录到求职进度')
    } else {
      // 当前已投 → 取消投递(复用删除求职进度接口)
      await request.delete(`/user/delete_application/${id}`)
      jobStore.appliedIds.delete(id)
      hasApplied.value = false
      ElMessage.success('已取消投递')
    }
  } catch (err) {
    if (err?.message) ElMessage.error(err.message)
  } finally {
    submitting.value = false
  }
}

const searchBySkill = (skill) => {
  router.push({ path: '/jobs', query: { keyword: skill.name } })
}

const goSimilar = (sj) => {
  if (sj.id) router.push(`/jobs/${sj.id}`)
}

import { onMounted, watch } from 'vue'
import request from '@/utils/request'
import { formatSalary } from '@/utils/format'

// 加载职位详情 + 相似职位 + 收藏状态(抽成函数, onMounted 和 watch 都能调)
const loadJobData = async (jobId) => {
  loading.value = true
  try {
    const [, similarRes] = await Promise.all([
      jobStore.fetchJobDetail(jobId),
      request.get(`/jobs/${jobId}/similar`)   // 相似职位
    ])
    job.value = jobStore.currentJob || {}
    similarJobs.value = similarRes || []       // 填充相似列表
    await jobStore.loadFavoriteIds()
    isFavorited.value = jobStore.isFavorited(Number(jobId))
    // 加载投递状态(进页面时显示按钮是"标记已投递"还是"已投递")
    await jobStore.loadAppliedIds()
    hasApplied.value = jobStore.isApplied(Number(jobId))
  } catch (e) {
    ElMessage.error('加载职位详情失败')
  } finally {
    loading.value = false
  }
}

// 首次进入页面
onMounted(() => loadJobData(route.params.id))

// 监听路由参数变化(从相似职位点进来时, onMounted 不触发, 靠 watch 重新加载)
watch(
  () => route.params.id,
  (newId) => {
    if (newId) loadJobData(newId)
  }
)
</script>

<style scoped>
.job-detail-page {
  min-height: 100vh;
}

.job-header {
  background: #fff;
  padding: 16px 0 24px;
  border-bottom: 1px solid #ebeef5;
}

.breadcrumb {
  margin-bottom: 16px;
}

.job-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.job-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.job-salary {
  font-size: 22px;
  color: #ff5722;
  font-weight: 600;
  margin-bottom: 12px;
}

.job-meta {
  display: flex;
  gap: 24px;
  color: #606266;
  font-size: 14px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.job-actions {
  display: flex;
  gap: 12px;
}

.source-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.publish-time {
  color: #909399;
  font-size: 13px;
}

.detail-body {
  margin-top: 20px;
}

.detail-card,
.company-card,
.similar-card {
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #303133;
}

.jd-content {
  line-height: 1.8;
  color: #303133;
  font-size: 14px;
  word-break: break-word;   /* 长文本自动换行 */
}

/* 加粗的小标题(岗位职责/任职要求等) */
.jd-content :deep(strong) {
  display: inline-block;
  margin-top: 12px;
  color: #409eff;
  font-weight: 600;
}
.jd-content :deep(strong:first-child) {
  margin-top: 0;   /* 第一个标题不要顶部间距 */
}

.jd-content :deep(p) {
  margin-bottom: 8px;
}

.skill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.advantage-content {
  color: #606266;
  line-height: 1.8;
}

.company-block {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.company-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.company-stage {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.company-desc {
  margin-top: 8px;
}

.welfare-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.similar-list {
  display: flex;
  flex-direction: column;
}

.similar-item {
  padding: 10px 0;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: color 0.2s;
}

.similar-item:last-child {
  border-bottom: none;
}

.similar-item:hover .similar-title {
  color: #409eff;
}

.similar-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
  font-weight: 500;
}

.similar-meta {
  font-size: 12px;
  color: #909399;
}

.apply-tip {
  margin-top: 16px;
  margin-bottom: 32px;
}
</style>
