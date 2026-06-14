<template>
  <div class="recommend-page page-container">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon color="#409eff"><MagicStick /></el-icon>
        智能推荐
      </h1>
      <p class="page-desc">基于你的简历技能档案,使用 AI 匹配算法推荐最合适的职位</p>
    </div>

    <!-- 简历选择 -->
    <el-card class="resume-selector" shadow="never">
      <div class="selector-inner">
        <div class="selector-info">
          <el-icon :size="32" color="#409eff"><Document /></el-icon>
          <div>
            <div class="selector-title">选择用于推荐的简历</div>
            <div class="selector-tip">不同简历可能得到不同推荐结果</div>
          </div>
        </div>
        <el-select v-model="selectedResumeId" placeholder="请选择简历" style="width: 280px">
          <el-option
            v-for="r in resumeList"
            :key="r.id"
            :label="r.title || `简历 #${r.id}`"
            :value="r.id"
          />
        </el-select>
        <el-button type="primary" :loading="recommending" @click="doRecommend">
          <el-icon><Refresh /></el-icon>
          {{ recommending ? '推荐中...' : '生成推荐' }}
        </el-button>
      </div>
    </el-card>

    <!-- 无简历提示 -->
    <el-empty v-if="!resumeList.length" description="你还没有简历,去上传一份吧?">
      <el-button type="primary" @click="goUploadResume">上传简历</el-button>
    </el-empty>

    <!-- 推荐结果为空 -->
    <el-empty
      v-else-if="!recommendations.length && !recommending"
      description="选择简历后点击「生成推荐」"
    />

    <!-- 推荐列表 -->
    <div v-else class="recommend-list" v-loading="recommending">
      <div
        v-for="(rec, idx) in recommendations"
        :key="rec.id"
        class="recommend-item"
      >
        <div class="match-score" :class="scoreLevel(rec.score)">
          <div class="score-circle">
            <span class="score-value">{{ rec.score }}</span>
            <span class="score-unit">分</span>
          </div>
          <div class="score-label">{{ scoreLevelText(rec.score) }}</div>
        </div>

        <div class="recommend-body">
          <div class="recommend-header">
            <h3 class="rec-title" @click="goJobDetail(rec)">{{ rec.title || rec.job?.title }}</h3>
            <span class="rec-salary">{{ rec.salary_text || salaryText(rec.job) }}</span>
          </div>

          <div class="rec-meta">
            <span>{{ rec.company_name || rec.job?.company_name }}</span>
            <el-divider direction="vertical" />
            <span>{{ rec.city || rec.job?.city }}</span>
            <el-divider direction="vertical" />
            <span>{{ rec.experience_req || rec.job?.experience_req }}</span>
          </div>

          <!-- 推荐理由 (LLM 生成) -->
          <div class="rec-reason">
            <el-icon color="#67c23a"><ChatLineSquare /></el-icon>
            <span>{{ rec.reason || '基于技能匹配度推荐' }}</span>
          </div>

          <!-- 技能匹配详情 -->
          <div class="skill-match" v-if="rec.matched_skills && rec.matched_skills.length">
            <span class="match-label">技能匹配:</span>
            <SkillTag
              v-for="s in rec.matched_skills"
              :key="s.id"
              :skill="s"
              size="small"
            />
          </div>

          <!-- 缺失技能 -->
          <div class="skill-miss" v-if="rec.missing_skills && rec.missing_skills.length">
            <span class="match-label">技能差距:</span>
            <el-tag
              v-for="s in rec.missing_skills"
              :key="s.id"
              type="danger"
              size="small"
              effect="plain"
            >
              {{ s.name }}
            </el-tag>
          </div>

          <div class="rec-actions">
            <el-button size="small" @click="goJobDetail(rec)">
              查看详情
            </el-button>
            <el-button size="small" type="primary" @click="goApply(rec)">
              <el-icon><Link /></el-icon>
              去投递
            </el-button>
            <el-tag size="small" type="info" effect="plain">
              策略: {{ strategyText(rec.strategy) }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import SkillTag from '@/components/common/SkillTag.vue'
// import { useResumeStore } from '@/stores/resume'
// import request from '@/utils/request'

const router = useRouter()
// const resumeStore = useResumeStore()

const resumeList = ref([])
const selectedResumeId = ref(null)
const recommendations = ref([])
const recommending = ref(false)

const salaryText = (job) => {
  if (!job) return ''
  if (!job.salary_min && !job.salary_max) return '薪资面议'
  return `${job.salary_min || ''}-${job.salary_max || ''}K`
}

const scoreLevel = (score) => {
  if (score >= 80) return 'level-high'
  if (score >= 60) return 'level-mid'
  return 'level-low'
}

const scoreLevelText = (score) => {
  if (score >= 80) return '高度匹配'
  if (score >= 60) return '较为匹配'
  return '一般匹配'
}

const strategyText = (s) => {
  const map = {
    rag: '向量召回',
    graph: '知识图谱',
    hybrid: '混合策略',
    cold_start: '冷启动'
  }
  return map[s] || s
}

const doRecommend = async () => {
  if (!selectedResumeId.value) {
    ElMessage.warning('请先选择简历')
    return
  }
  recommending.value = true
  // TODO: 调用推荐接口
  // try {
  //   const res = await request.get('/recommendations', {
  //     params: { resumeId: selectedResumeId.value, limit: 20 }
  //   })
  //   recommendations.value = res.list
  //   ElMessage.success(`已生成 ${res.list.length} 条推荐`)
  // } finally {
  //   recommending.value = false
  // }
  console.log('[TODO] doRecommend', selectedResumeId.value)
  setTimeout(() => {
    recommending.value = false
  }, 300)
}

const goJobDetail = (rec) => {
  const jobId = rec.job_id || rec.job?.id
  if (jobId) router.push(`/jobs/${jobId}`)
}

const goApply = (rec) => {
  const url = rec.source_url || rec.job?.source_url
  if (!url) {
    ElMessage.warning('未找到原站链接')
    return
  }
  // TODO: 记录跳转 applications.status='clicked'
  window.open(url, '_blank', 'noopener')
}

const goUploadResume = () => router.push('/resume')

// TODO: 加载简历列表
// import { onMounted } from 'vue'
// onMounted(async () => {
//   await resumeStore.fetchResumeList()
//   resumeList.value = resumeStore.resumeList
//   if (resumeList.value.length) {
//     selectedResumeId.value = resumeList.value[0].id
//   }
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

.resume-selector {
  margin-bottom: 24px;
}

.selector-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.selector-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.selector-title {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.selector-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.recommend-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recommend-item {
  display: flex;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.recommend-item:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.match-score {
  flex: 0 0 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 12px;
  color: #fff;
}

.level-high {
  background: linear-gradient(135deg, #67c23a, #4eaa1d);
}

.level-mid {
  background: linear-gradient(135deg, #409eff, #1f7fe0);
}

.level-low {
  background: linear-gradient(135deg, #e6a23c, #c4851a);
}

.score-circle {
  text-align: center;
  margin-bottom: 8px;
}

.score-value {
  font-size: 36px;
  font-weight: 700;
}

.score-unit {
  font-size: 13px;
  margin-left: 2px;
}

.score-label {
  font-size: 13px;
  opacity: 0.95;
}

.recommend-body {
  flex: 1;
  padding: 16px 24px;
  min-width: 0;
}

.recommend-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.rec-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
  cursor: pointer;
}

.rec-title:hover {
  color: #409eff;
}

.rec-salary {
  font-size: 16px;
  color: #ff5722;
  font-weight: 600;
}

.rec-meta {
  color: #606266;
  font-size: 13px;
  margin-bottom: 12px;
}

.rec-reason {
  background: #f0f9eb;
  padding: 8px 12px;
  border-radius: 4px;
  display: flex;
  gap: 6px;
  align-items: flex-start;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.skill-match,
.skill-miss {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.match-label {
  font-size: 13px;
  color: #909399;
  margin-right: 4px;
}

.rec-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
}
</style>
