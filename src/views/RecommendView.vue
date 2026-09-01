<template>
  <div class="recommend-page page-container">
    <!-- 简历选择区 -->
    <el-card class="resume-card" shadow="never" v-loading="resumeLoading">
      <template #header>
        <div class="card-title">
          <span>选择推荐用的简历</span>
          <el-button text @click="goResumeManage">
            <el-icon><Setting /></el-icon>
            管理简历
          </el-button>
        </div>
      </template>

      <el-empty v-if="!resumeList.length && !resumeLoading" description="还没有简历">
        <el-button type="primary" @click="goResumeManage">去上传简历</el-button>
      </el-empty>

      <!-- 简历多了改用下拉选择(可滚动/可输入筛选), 不再平铺占满页面 -->
      <el-select
        v-else
        v-model="selectedResumeId"
        placeholder="选择推荐用的简历"
        class="resume-select"
        size="large"
        filterable
      >
        <el-option
          v-for="r in resumeList"
          :key="r.id"
          :value="r.id"
          :label="r.title || r.name"
        >
          <div class="resume-option">
            <span class="resume-name">{{ r.title || r.name }}</span>
            <el-tag v-if="r.is_primary" size="small" type="success">默认</el-tag>
            <span class="resume-meta">
              {{ r.work_years || '工作年限未知' }} · {{ r.education || '学历未知' }}
            </span>
          </div>
        </el-option>
      </el-select>
    </el-card>

    <!-- 推荐操作 + 结果区 -->
    <el-card class="result-card" shadow="never">
      <template #header>
        <div class="card-title">
          <span>推荐结果</span>
          <span class="header-hint">技能召回 + 向量召回 + LLM 重排</span>
          <el-button
            type="primary"
            :loading="recommendLoading"
            :disabled="!selectedResumeId"
            @click="doRecommend"
          >
            <el-icon v-if="!recommendLoading"><MagicStick /></el-icon>
            {{ recommendLoading ? 'AI 匹配中...' : '开始推荐' }}
          </el-button>
        </div>
      </template>

      <!-- 加载骨架屏(推荐中) -->
      <div v-if="recommendLoading" class="skeleton-list">
        <el-skeleton :rows="4" animated v-for="n in 3" :key="n" class="skeleton-item" />
      </div>

      <!-- 空态 -->
      <el-empty
        v-else-if="!recommendItems.length"
        :description="hasRecommended ? '没有匹配的岗位,试试补充简历技能' : '选择简历后点「开始推荐」'"
      />

      <!-- 推荐结果列表 -->
      <div v-else class="recommend-list">
        <div
          v-for="(item, idx) in recommendItems"
          :key="item.job.id"
          class="recommend-item"
        >
          <!-- 外层: 排名 + 分数 + 策略标签 + 推荐理由(这些是推荐特有的, JobCard 没有) -->
          <div class="recommend-meta">
            <div class="rank-score">
              <span class="rank" :class="rankClass(idx)">{{ idx + 1 }}</span>
              <div class="score-box">
                <div class="score-num">{{ Math.round(item.score) }}</div>
                <div class="score-label">匹配分</div>
              </div>
            </div>
          </div>

          <!-- 中层: 推荐理由 + 策略(在 JobCard 之上独立展示) -->
          <div class="recommend-reason" v-if="item.reason">
            <el-icon color="#67c23a"><ChatDotRound /></el-icon>
            <span>{{ item.reason }}</span>
            <el-tag size="small" effect="plain" class="strategy-tag">
              {{ strategyText(item.strategy) }}
            </el-tag>
          </div>

          <!-- 内层: 复用通用 JobCard 渲染职位本身, 不改 JobCard -->
          <router-link :to="`/jobs/${item.job.id}`" class="job-link">
            <JobCard :job="item.job" />
          </router-link>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
// 声明组件 name 给 keep-alive 的 include 匹配用
// <script setup> 不支持直接写 name, 要配一个并列的普通 <script> 块
// (Vue 3 SFC 允许 <script setup> 和 <script> 同时存在, 后者用来定义 name 等)
// 注意: 本项目路由 name 'Recommend' 已被 AI 求职顾问(ChatView)占用,
//       本组件用 'JobRecommend' 区分, 页面路由为 /job-recommend
export default {
  name: 'JobRecommend'
}
</script>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '@/utils/request'
import JobCard from '@/components/common/JobCard.vue'

const route = useRoute()
const router = useRouter()

// ---------- 简历选择 ----------
const resumeLoading = ref(false)
const resumeList = ref([])
const selectedResumeId = ref(null)

// ---------- 推荐结果 ----------
const recommendLoading = ref(false)
const hasRecommended = ref(false) // 是否已经请求过(区分"没点推荐"和"推了但没结果"两种空态)
const recommendResult = ref(null) // 后端返回的 RecommendOut

// 推荐 items 拆出来方便模板用
const recommendItems = computed(() => recommendResult.value?.items || [])

// ---------- 拉简历列表 ----------
async function loadResumes() {
  resumeLoading.value = true
  try {
    const list = await request.get('/resumes/all')
    resumeList.value = list || []
    // 优先用 query 传来的 resumeId, 其次用默认简历, 最后取第一个
    if (route.query.resumeId) {
      selectedResumeId.value = Number(route.query.resumeId)
    } else {
      const primary = resumeList.value.find((r) => r.is_primary)
      selectedResumeId.value = primary?.id || resumeList.value[0]?.id || null
    }
  } catch (e) {
    resumeList.value = []
  } finally {
    resumeLoading.value = false
  }
}

// ---------- 触发推荐 ----------
async function doRecommend() {
  if (!selectedResumeId.value) return
  recommendLoading.value = true
  recommendResult.value = null
  try {
    // request 拦截器会自动解包 {code,message,data}, 这里拿到的就是 RecommendOut 本体
    const data = await request.get('/recommend', {
      params: { resume_id: selectedResumeId.value }
    })
    recommendResult.value = data
  } catch (e) {
    recommendResult.value = null
  } finally {
    recommendLoading.value = false
    hasRecommended.value = true
  }
}

// ---------- 辅助: 排名样式 ----------
function rankClass(idx) {
  if (idx === 0) return 'rank-gold'      // 第 1 名金色
  if (idx === 1) return 'rank-silver'    // 第 2 名银色
  if (idx === 2) return 'rank-bronze'    // 第 3 名铜色
  return ''
}

// ---------- 辅助: 策略标签文案 ----------
function strategyText(strategy) {
  const map = {
    skill: '技能匹配',
    hybrid: '技能+语义',
    rag: 'AI 重排'
  }
  return map[strategy] || strategy
}

function goResumeManage() {
  router.push('/resume')
}

onMounted(() => {
  loadResumes()
})
</script>

<style scoped>
.header-hint {
  flex: 1;
  text-align: left;
  margin-left: 12px;
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}

.resume-card,
.result-card {
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.resume-select {
  width: 100%;
  max-width: 520px;
}

.resume-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.resume-option .resume-meta {
  margin-left: auto;
}

.resume-name {
  font-weight: 600;
  color: #303133;
}

.resume-meta {
  color: #909399;
  font-size: 13px;
}

/* ---------- 骨架屏 ---------- */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.skeleton-item {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

/* ---------- 推荐结果项 ---------- */
.recommend-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recommend-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
  transition: box-shadow 0.2s;
}

.recommend-item:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

/* 顶部 meta 行: 左边排名+分数, 右边留空 */
.recommend-meta {
  margin-bottom: 8px;
}

.rank-score {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 排名圆形徽章 */
.rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #c0c4cc;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
}

.rank-gold {
  background: linear-gradient(135deg, #ffd700, #ffb700);
}
.rank-silver {
  background: linear-gradient(135deg, #c0c0c0, #a8a8a8);
}
.rank-bronze {
  background: linear-gradient(135deg, #cd7f32, #b87333);
}

/* 分数方块 */
.score-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.1;
}

.score-num {
  font-size: 20px;
  font-weight: 700;
  color: #67c23a;
}

.score-label {
  font-size: 11px;
  color: #909399;
}

/* 推荐理由行 */
.recommend-reason {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0 12px 40px; /* 40px 对齐排名徽章右边 */
  padding: 6px 10px;
  background: #f0f9eb;
  border-left: 3px solid #67c23a;
  border-radius: 0 4px 4px 0;
  font-size: 13px;
  color: #606266;
}

.strategy-tag {
  margin-left: auto;
}

/* JobCard 链接包裹: 去掉默认下划线 */
.job-link {
  display: block;
  text-decoration: none;
  color: inherit;
}
</style>
