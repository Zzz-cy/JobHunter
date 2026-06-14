<template>
  <div class="job-list-page page-container">
    <!-- 搜索栏 -->
    <el-card class="search-card" shadow="never">
      <el-input
        v-model="filters.keyword"
        placeholder="职位名 / 技能 / 公司"
        size="large"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>

      <div class="filter-row">
        <el-select v-model="filters.city" placeholder="城市" clearable style="width: 140px">
          <el-option v-for="c in cityOptions" :key="c" :label="c" :value="c" />
        </el-select>

        <el-select v-model="filters.experience" placeholder="经验" clearable style="width: 140px">
          <el-option v-for="e in experienceOptions" :key="e" :label="e" :value="e" />
        </el-select>

        <el-select v-model="filters.education" placeholder="学历" clearable style="width: 140px">
          <el-option v-for="e in educationOptions" :key="e" :label="e" :value="e" />
        </el-select>

        <el-cascader
          v-model="filters.industry"
          :options="industryOptions"
          placeholder="行业"
          clearable
          :props="{ checkStrictly: true, emitPath: false }"
          style="width: 180px"
        />

        <el-select v-model="filters.salaryRange" placeholder="薪资" clearable style="width: 160px">
          <el-option label="不限" value="" />
          <el-option label="10K 以下" value="0-10" />
          <el-option label="10-20K" value="10-20" />
          <el-option label="20-30K" value="20-30" />
          <el-option label="30-50K" value="30-50" />
          <el-option label="50K 以上" value="50-" />
        </el-select>

        <el-select v-model="filters.source" placeholder="来源" clearable style="width: 120px">
          <el-option label="Boss直聘" value="boss" />
          <el-option label="猎聘" value="liepin" />
          <el-option label="官网" value="official" />
        </el-select>

        <div class="filter-actions">
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>
      </div>
    </el-card>

    <!-- 结果区 -->
    <div class="result-container">
      <!-- 左侧:结果列表 -->
      <div class="result-main">
        <div class="result-header">
          <span class="result-count">
            共 <strong>{{ total }}</strong> 个职位
          </span>
          <el-radio-group v-model="sortBy" size="small">
            <el-radio-button label="default">综合</el-radio-button>
            <el-radio-button label="latest">最新</el-radio-button>
            <el-radio-button label="salary">薪资</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 空状态 -->
        <el-empty v-if="!loading && jobList.length === 0" description="暂无符合条件的职位,试试调整筛选条件?" />

        <!-- 加载骨架屏 -->
        <div v-if="loading">
          <el-skeleton v-for="i in 5" :key="i" :rows="4" animated class="skeleton-card" />
        </div>

        <!-- 职位卡片列表 -->
        <div v-else class="job-list">
          <JobCard
            v-for="job in jobList"
            :key="job.id"
            :job="job"
            @click="goJobDetail"
          />
        </div>

        <!-- 分页 -->
        <div class="pagination" v-if="total > 0">
          <el-pagination
            v-model:current-page="filters.page"
            v-model:page-size="filters.pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @current-change="handleSearch"
            @size-change="handleSearch"
          />
        </div>
      </div>

      <!-- 右侧:推荐 / 收藏侧栏 -->
      <div class="result-aside">
        <el-card class="aside-card" shadow="never">
          <template #header>
            <div class="aside-title">
              <el-icon color="#409eff"><MagicStick /></el-icon>
              快速匹配
            </div>
          </template>
          <p class="aside-desc">上传简历,AI 自动匹配高薪职位</p>
          <el-button type="primary" plain class="aside-btn" @click="goResume">
            上传简历
          </el-button>
          <el-button class="aside-btn" @click="goRecommend">查看推荐</el-button>
        </el-card>

        <el-card class="aside-card" shadow="never">
          <template #header>
            <div class="aside-title">
              <el-icon color="#f56c6c"><Hot /></el-icon>
              热门搜索
            </div>
          </template>
          <div class="aside-tags">
            <el-tag
              v-for="kw in hotKeywords"
              :key="kw"
              class="aside-tag"
              effect="plain"
              @click="quickSearch(kw)"
            >
              {{ kw }}
            </el-tag>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import JobCard from '@/components/common/JobCard.vue'
// import { useJobStore } from '@/stores/job'

const router = useRouter()
const route = useRoute()
// const jobStore = useJobStore()

const loading = ref(false)
const total = ref(0)
const jobList = ref([])
const sortBy = ref('default')

const filters = reactive({
  keyword: route.query.keyword || '',
  city: '',
  experience: '',
  education: '',
  industry: '',
  salaryRange: '',
  source: '',
  page: 1,
  pageSize: 20
})

const cityOptions = ['北京', '上海', '深圳', '广州', '杭州', '成都', '南京', '武汉', '西安', '苏州', '其他']
const experienceOptions = ['应届', '1-3年', '3-5年', '5-10年', '10年以上', '不限']
const educationOptions = ['大专', '本科', '硕士', '博士', '不限']
const industryOptions = [
  {
    value: 'IT', label: '互联网/IT',
    children: [
      { value: 'IT-RD', label: '研发' },
      { value: 'IT-DATA', label: '数据' },
      { value: 'IT-PM', label: '产品' }
    ]
  },
  {
    value: 'FIN', label: '金融',
    children: [{ value: 'FIN-BANK', label: '银行' }, { value: 'FIN-SEC', label: '证券' }]
  }
]
const hotKeywords = ['Python', 'Java', '前端', '数据分析', '产品经理', '运营']

const handleSearch = () => {
  // TODO: 调用 store 或接口查询职位
  // await jobStore.fetchJobList()
  // jobList.value = jobStore.jobList
  // total.value = jobStore.total
  console.log('[TODO] search with filters:', { ...filters, sort: sortBy.value })
}

const handleReset = () => {
  Object.assign(filters, {
    keyword: '',
    city: '',
    experience: '',
    education: '',
    industry: '',
    salaryRange: '',
    source: '',
    page: 1
  })
  handleSearch()
}

const quickSearch = (kw) => {
  filters.keyword = kw
  handleSearch()
}

const goJobDetail = (job) => {
  if (job.id) router.push(`/jobs/${job.id}`)
}

const goResume = () => router.push('/resume')
const goRecommend = () => router.push('/recommend')

// TODO: 初始化加载第一页
// import { onMounted } from 'vue'
// onMounted(() => {
//   handleSearch()
// })
</script>

<style scoped>
.search-card {
  margin-bottom: 16px;
  padding: 12px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  align-items: center;
}

.filter-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.result-container {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.result-main {
  flex: 1;
  min-width: 0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 0 4px;
}

.result-count {
  color: #606266;
  font-size: 13px;
}

.result-count strong {
  color: #ff5722;
  font-size: 15px;
  margin: 0 4px;
}

.skeleton-card {
  padding: 16px;
  background: #fff;
  margin-bottom: 12px;
  border-radius: 4px;
}

.pagination {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.result-aside {
  flex: 0 0 280px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.aside-card {
  padding: 4px;
}

.aside-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #303133;
}

.aside-desc {
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}

.aside-btn {
  width: 100%;
  margin-bottom: 8px;
  margin-left: 0 !important;
}

.aside-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.aside-tag {
  cursor: pointer;
}
</style>
