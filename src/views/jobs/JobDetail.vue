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
            <div class="job-salary">{{ salaryText }}</div>

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
            <el-button
              :type="isFavorited ? 'warning' : 'default'"
              size="large"
              @click="toggleFavorite"
            >
              <el-icon><Star v-if="!isFavorited" /><StarFilled v-else /></el-icon>
              {{ isFavorited ? '已收藏' : '收藏' }}
            </el-button>

            <el-button type="primary" size="large" @click="goExternalApply">
              <el-icon><Link /></el-icon>
              去原网站投递
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
            <div class="jd-content" v-html="job.description || job.description_text || '暂无描述'">
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
                :key="skill.id || skill.name"
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
              <el-avatar :size="56" :src="job.company_logo">
                {{ (job.company_name || '?').charAt(0) }}
              </el-avatar>
              <div class="company-name-block">
                <div class="company-name">{{ job.company_name }}</div>
                <div class="company-stage">{{ job.company_stage || '融资阶段未知' }}</div>
              </div>
            </div>

            <el-descriptions :column="1" class="company-desc">
              <el-descriptions-item label="行业">
                {{ job.industry_name || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="规模">
                {{ job.company_size || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="城市">
                {{ job.company_city || job.city || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="官网" v-if="job.company_website">
                <a :href="job.company_website" target="_blank" rel="noopener">
                  {{ job.company_website }}
                </a>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 福利标签 -->
            <div class="welfare-tags" v-if="job.company_welfare && job.company_welfare.length">
              <el-tag
                v-for="w in job.company_welfare"
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
                  {{ sj.salary_text || '薪资面议' }} · {{ sj.company_name }}
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
// import { useJobStore } from '@/stores/job'

const route = useRoute()
const router = useRouter()
// const jobStore = useJobStore()

const loading = ref(false)
const job = ref({})
const similarJobs = ref([])
const isFavorited = ref(false)

const salaryText = computed(() => {
  const j = job.value
  if (!j.salary_min && !j.salary_max) return '薪资面议'
  const unit = j.salary_unit === 'day' ? '元/天' : j.salary_unit === 'year' ? 'K/年' : 'K'
  if (j.salary_min && j.salary_max) {
    return `${j.salary_min}-${j.salary_max}${unit}${j.salary_months ? `·${j.salary_months}薪` : ''}`
  }
  return `${j.salary_min || j.salary_max}${unit}`
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

const toggleFavorite = () => {
  // TODO: 调用 store 收藏接口
  // await jobStore.toggleFavorite(route.params.id)
  // isFavorited.value = jobStore.isFavorited(route.params.id)
  isFavorited.value = !isFavorited.value
  ElMessage.success(isFavorited.value ? '已收藏' : '已取消收藏')
}

const goExternalApply = () => {
  if (!job.value.source_url) {
    ElMessage.warning('未找到原站链接')
    return
  }
  // TODO: 记录点击事件, INSERT INTO applications (status='clicked')
  // await jobStore.recordClick(route.params.id)
  ElMessage.info('即将跳转到原网站...')
  window.open(job.value.source_url, '_blank', 'noopener')
}

const searchBySkill = (skill) => {
  router.push({ path: '/jobs', query: { keyword: skill.name } })
}

const goSimilar = (sj) => {
  if (sj.id) router.push(`/jobs/${sj.id}`)
}

// TODO: 加载职位详情、相似职位、收藏状态
// import { onMounted } from 'vue'
// onMounted(async () => {
//   loading.value = true
//   try {
//     const [detail, similar] = await Promise.all([
//       request.get(`/jobs/${route.params.id}`),
//       request.get(`/jobs/${route.params.id}/similar`, { params: { limit: 5 } })
//     ])
//     job.value = detail
//     similarJobs.value = similar.list
//     isFavorited.value = detail.is_favorited
//   } finally {
//     loading.value = false
//   }
// })
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
