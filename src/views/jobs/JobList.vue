<template>
  <div class="job-list-page page-container">
    <!-- 搜索栏 -->
    <el-card class="search-card" shadow="never">
      <div class="search-row">
        <el-input
          v-model="filters.keyword"
          placeholder="职位名 / 技能 / 公司"
          size="large"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <!-- 右侧快捷入口:提醒用户有这两个功能 -->
        <el-button
          size="large"
          plain
          @click="goFavorites"
        >
          <el-icon><Star /></el-icon>
          <span>我的收藏</span>
        </el-button>
        <el-button
          size="large"
          plain
          @click="goApplications"
        >
          <el-icon><Document /></el-icon>
          <span>求职进度</span>
        </el-button>
      </div>

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
          <el-radio-group v-model="sortBy" size="small" @change="handleSortChange">
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
            :page-size="10"
            :total="total"
            layout="total, prev, pager, next, jumper"
            background
            @current-change="handleSearch"
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
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, Star, Document } from '@element-plus/icons-vue'
import JobCard from '@/components/common/JobCard.vue'
import { useJobStore } from '@/stores/job'

const router = useRouter()
const route = useRoute()
const jobStore = useJobStore()

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
  pageSize: 10
})

const cityOptions = ['北京', '上海', '深圳', '广州', '杭州', '成都', '南京', '武汉', '西安', '苏州', '其他']
const experienceOptions = ['应届', '1-3年', '3-5年', '5-10年', '10年以上', '不限']
const educationOptions = ['大专', '本科', '硕士', '博士', '不限']

// 把后端返回的扁平行业列表, 转成 el-cascader 需要的树状结构
const buildIndustryTree = (flatList) => {
  // 1. 先把每个节点转成 {value, label}, 并建一个 id → 节点 的映射
  const nodeMap = {}
  flatList.forEach(item => {
    nodeMap[item.id] = {
      value: item.code,
      label: item.name,
      children: []
    }
  })
  // 2. 遍历一遍, 把子节点塞到父节点的 children 里
  const tree = []
  flatList.forEach(item => {
    if (item.parent_id === null) {
      // 一级行业, 直接放进结果数组
      tree.push(nodeMap[item.id])
    } else {
      // 二级行业, 塞到对应的父节点下
      const parent = nodeMap[item.parent_id]
      if (parent) {
        parent.children.push(nodeMap[item.id])
      }
    }
  })
  // 3. 清理: 没有子节点的, children 设为 undefined(级联不显示展开箭头)
  tree.forEach(node => {
    if (node.children.length === 0) {
      delete node.children
    }
  })
  return tree
}

const industryOptions = computed(() => buildIndustryTree(jobStore.industries || []))

// 热门搜索词
const hotKeywords = computed(() => jobStore.hots || [])

const handleSearch = async () => {
  // 把过滤条件同步到 store(薪资范围拆分等转换逻辑由 store 负责)
  jobStore.setQueryParams(filters)
  jobStore.queryParams.sort = sortBy.value
  await jobStore.fetchJobList()
  jobList.value = jobStore.jobList
  total.value = jobStore.total
}

// 切换排序方式 = 重新搜索(回第 1 页), 复用 handleSearch 避免代码重复
const handleSortChange = () => {
  filters.page = 1
  handleSearch()
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

// 跳转到个人中心的"我的收藏"(左侧菜单 tab: favorites)
const goFavorites = () => router.push({ path: '/profile', query: { tab: 'favorites' } })

// 跳转到个人中心的"求职进度"(左侧菜单 tab: jobs)
const goApplications = () => router.push({ path: '/profile', query: { tab: 'jobs' } })

const goResume = () => router.push('/resume')
const goRecommend = () => router.push('/recommend')

import { onMounted } from 'vue'
onMounted(async () => {
  // 并行加载: 行业字典 + 职位列表(互不依赖, 用 Promise.all 提速)
  await Promise.all([
    jobStore.getIndustries(),
    jobStore.getHots(),
    handleSearch()
  ])
})
</script>

<style scoped>
.search-card {
  margin-bottom: 16px;
  padding: 12px;
}

/* 搜索框 + 右侧快捷入口同一行 */
.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.search-input {
  flex: 1;   /* 搜索框占满剩余空间 */
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
