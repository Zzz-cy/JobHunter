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
        :key="rec.id || idx"
        class="recommend-item"
      >
        <div class="rec-rank">#{{ idx + 1 }}</div>
        <div class="rec-main">
          <JobCard :job="rec.job || rec" @click="goJobDetail(rec)" />
          <div class="rec-extra" v-if="rec.score || rec.reason">
            <el-tag v-if="rec.score" type="success" effect="dark" size="small">
              匹配度 {{ rec.score }}分
            </el-tag>
            <span v-if="rec.reason" class="rec-reason">{{ rec.reason }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MagicStick, Document, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import JobCard from '@/components/common/JobCard.vue'
import { useResumeStore } from '@/stores/resume'
import request from '@/utils/request'

const router = useRouter()
const resumeStore = useResumeStore()

const selectedResumeId = ref(null)
const resumeList = ref([])
const recommendations = ref([])
const recommending = ref(false)

// 加载简历列表
const loadResumes = async () => {
  try {
    await resumeStore.fetchResumeList()
    resumeList.value = resumeStore.resumeList
    // 自动选第一份
    if (resumeList.value.length > 0) {
      selectedResumeId.value = resumeList.value[0].id
    }
  } catch (err) {
    console.error('加载简历失败', err)
  }
}

// 生成推荐
const doRecommend = async () => {
  if (!selectedResumeId.value) {
    ElMessage.warning('请先选择简历')
    return
  }
  recommending.value = true
  try {
    const data = await request.get('/recommend', {
      params: { resume_id: selectedResumeId.value }
    })
    recommendations.value = data?.list || data || []
    if (recommendations.value.length === 0) {
      ElMessage.info('暂无推荐结果,试试完善简历?')
    }
  } catch (err) {
    console.error('推荐失败', err)
  } finally {
    recommending.value = false
  }
}

const goJobDetail = (rec) => {
  const jobId = rec.job?.id || rec.id
  if (jobId) router.push(`/jobs/${jobId}`)
}

const goUploadResume = () => router.push('/resume')

onMounted(() => {
  loadResumes()
})
</script>

<style scoped>
.recommend-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-desc {
  color: #909399;
  font-size: 13px;
  margin-top: 6px;
}

.resume-selector {
  margin-bottom: 20px;
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
  font-weight: 600;
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
  gap: 16px;
  align-items: flex-start;
}

.rec-rank {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.rec-main {
  flex: 1;
  min-width: 0;
}

.rec-extra {
  margin-top: 8px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.rec-reason {
  font-size: 13px;
  color: #606266;
  flex: 1;
}
</style>
