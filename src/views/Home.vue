<template>
  <div class="home-page">
    <!-- Hero 搜索区 -->
    <section class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">
          找到你的<span class="highlight">理想工作</span>
        </h1>
        <p class="hero-subtitle">
          聚合 Boss / 猎聘 / 官网直招 · AI 智能匹配 · 知识图谱推荐
        </p>

        <div class="search-box">
          <el-input
            v-model="keyword"
            placeholder="搜索职位、技能、公司..."
            size="large"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" size="large" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </div>

        <!-- 热门关键词 -->
        <div class="hot-keywords">
          <span class="hot-label">热门:</span>
          <el-tag
            v-for="kw in hotKeywords"
            :key="kw"
            class="hot-tag"
            effect="plain"
            @click="searchByKeyword(kw)"
          >
            {{ kw }}
          </el-tag>
        </div>
      </div>
    </section>

    <!-- 数据统计区 -->
    <section class="stats-section">
      <div class="page-container">
        <el-row :gutter="20">
          <el-col :span="6" v-for="stat in stats" :key="stat.label">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </section>

    <!-- 热门职位 -->
    <section class="hot-jobs-section page-container">
      <div class="section-header">
        <h2 class="section-title">
          <el-icon color="#ff5722"><Hot /></el-icon>
          热门职位
        </h2>
        <el-button text @click="goJobList">
          查看全部
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      <el-row :gutter="16">
        <el-col :span="8" v-for="job in hotJobs" :key="job.id">
          <JobCard :job="job" @click="goJobDetail" />
        </el-col>
      </el-row>
    </section>

    <!-- 平台特色 -->
    <section class="features-section page-container">
      <h2 class="section-title">平台特色</h2>
      <el-row :gutter="20">
        <el-col :span="6" v-for="feat in features" :key="feat.title">
          <el-card class="feature-card" shadow="hover">
            <el-icon :size="40" :color="feat.color">
              <component :is="feat.icon" />
            </el-icon>
            <h3>{{ feat.title }}</h3>
            <p>{{ feat.desc }}</p>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import JobCard from '@/components/common/JobCard.vue'
// import { useJobStore } from '@/stores/job'

const router = useRouter()
// const jobStore = useJobStore()

const keyword = ref('')

const hotKeywords = ['Python 后端', '前端工程师', '数据分析师', 'Java 开发', '产品经理', 'AI 算法']

const stats = ref([
  { label: '在招职位', value: '0' },
  { label: '入驻公司', value: '0' },
  { label: '技能字典', value: '0' },
  { label: '行业覆盖', value: '0' }
])

const hotJobs = ref([])

const features = [
  {
    icon: 'MagicStick',
    title: 'AI 智能推荐',
    desc: '基于简历的技能匹配 + 衰减加权算法,精准推送高匹配度职位',
    color: '#409eff'
  },
  {
    icon: 'Share',
    title: '知识图谱',
    desc: 'Neo4j 构建技能图谱,挖掘技能关联,拓展你可能感兴趣的岗位',
    color: '#67c23a'
  },
  {
    icon: 'Document',
    title: '简历智能解析',
    desc: 'PDF/图片简历 OCR + NER 抽取,自动建立技能档案',
    color: '#e6a23c'
  },
  {
    icon: 'DataAnalysis',
    title: '行业数据洞察',
    desc: '薪资分布、技能热度、行业趋势,数据驱动你的求职决策',
    color: '#f56c6c'
  }
]

const handleSearch = () => {
  router.push({ path: '/jobs', query: { keyword: keyword.value } })
}

const searchByKeyword = (kw) => {
  keyword.value = kw
  handleSearch()
}

const goJobList = () => router.push('/jobs')

const goJobDetail = (job) => {
  if (job.id) router.push(`/jobs/${job.id}`)
}

// TODO: 组件挂载时加载统计数据和热门职位
// import { onMounted } from 'vue'
// onMounted(async () => {
//   const [statRes, hotRes] = await Promise.all([
//     request.get('/stats/overview'),
//     request.get('/jobs/hot', { params: { limit: 6 } })
//   ])
//   stats.value = [
//     { label: '在招职位', value: statRes.jobCount },
//     { label: '入驻公司', value: statRes.companyCount },
//     { label: '技能字典', value: statRes.skillCount },
//     { label: '行业覆盖', value: statRes.industryCount }
//   ]
//   hotJobs.value = hotRes.list
// })
</script>

<style scoped>
.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 80px 20px 100px;
  color: #fff;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 16px;
}

.highlight {
  color: #ffd54f;
}

.hero-subtitle {
  font-size: 16px;
  margin-bottom: 40px;
  opacity: 0.9;
}

.search-box {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.hot-keywords {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hot-label {
  opacity: 0.8;
  font-size: 13px;
}

.hot-tag {
  cursor: pointer;
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

.hot-tag:hover {
  background: rgba(255, 255, 255, 0.3);
}

.stats-section {
  margin-top: -60px;
  position: relative;
  z-index: 2;
}

.stat-card {
  text-align: center;
  padding: 12px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 32px 0 16px;
}

.section-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.features-section {
  margin: 32px auto 48px;
}

.feature-card {
  text-align: center;
  padding: 16px;
  height: 100%;
}

.feature-card h3 {
  font-size: 16px;
  margin: 12px 0 8px;
  color: #303133;
}

.feature-card p {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
</style>
