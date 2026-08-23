import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useJobStore = defineStore('job', {
  state: () => ({
    // 职位列表
    jobList: [],
    total: 0,
    loading: false,

    // 当前职位详情
    currentJob: null,
    //行业字典
    industries: null,
    //热门搜索词
    hots: [],
    // 查询条件
    queryParams: {
      keyword: '',
      city: '',
      salaryRange: null,     // 薪资区间字符串如 "20-30", 后端按 K 解析后转元查库
      experience: '',
      education: '',
      industry: '',
      source: '',
      sort: 'default',      // 排序方式: default(综合) / latest(最新) / salary(薪资)
      page: 1,
      pageSize: 10          // 固定每页 10 条(去掉用户切换, 避免 size-change 时序坑)
    },

    // 收藏的职位 id 集合
    favoriteIds: new Set(),

    // 已投递的职位 id 集合(用户点过"标记已投递")
    appliedIds: new Set(),
    favoritesLoaded: false,   // 标记: 收藏列表是否已加载过(避免重复请求)
    appliedLoaded: false      // 标记: 投递列表是否已加载过
  }),

  getters: {
    isFavorited: (state) => (jobId) => state.favoriteIds.has(jobId),
    isApplied: (state) => (jobId) => state.appliedIds.has(jobId)
  },

  actions: {
    // salaryRange 是 "20-30" 这种字符串, 原样传给后端会把它从 K 转成元再查库(数据库存元)
    setQueryParams(filters) {
      const { salaryRange, ...rest } = filters
      Object.assign(this.queryParams, {
        ...rest,
        salaryRange: salaryRange || null
      })
    },

    // 查询职位列表
    async fetchJobList() {
      this.loading = true
      try {
        // ⚠️ 后端字段用下划线命名(salary_range / page_size),
        // 前端 store 用驼峰, 这里发请求前必须转换, 否则后端收不到
        const params = {
          ...this.queryParams,
          salary_range: this.queryParams.salaryRange,
          page_size: this.queryParams.pageSize,
        }
        delete params.salaryRange
        delete params.pageSize
        const res = await request.get('/jobs/page', { params })
        this.jobList = res.items
        this.total = res.total
      } finally {
        this.loading = false
      }
    },

    // 获取职位详情
    async fetchJobDetail(id) {
      const res = await request.get(`/jobs/${id}`)
      this.currentJob = res
    },

    //获取行业字典
    async getIndustries(){
      this.industries = await request.get('/jobs/industries')
    },

    //获取热门搜索词
    async getHots(){
      this.hots = await request.get('/jobs/hot-keywords')
    },

    // 从后端加载我收藏的职位 id 列表(进详情页时调一次)
    async loadFavoriteIds() {
      if (this.favoritesLoaded) return    // 已加载过就不重复请求
      const ids = await request.get('/jobs/applications/favorite-ids')
      this.favoriteIds = new Set(ids)
      this.favoritesLoaded = true
    },

    // 从后端加载我已投递的职位 id 列表(进详情页时调一次)
    async loadAppliedIds() {
      if (this.appliedLoaded) return
      const ids = await request.get('/jobs/applications/applied-ids')
      this.appliedIds = new Set(ids)
      this.appliedLoaded = true
    },

    // 收藏/取消收藏(jobId 统一转 Number, 和后端返回的数字 id 对齐)
    async toggleFavorite(jobId) {
      const id = Number(jobId)
      if (this.favoriteIds.has(id)) {
        await request.delete(`/jobs/applications/${id}/favorite`)
        this.favoriteIds.delete(id)
      } else {
        await request.post(`/jobs/applications/${id}/favorite`)
        this.favoriteIds.add(id)
      }
    },
  }
})
