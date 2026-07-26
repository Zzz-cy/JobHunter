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
      salaryMin: null,
      salaryMax: null,
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
    // 把组件本地的过滤条件同步到 store.queryParams(发请求真正用的字段)
    // salaryRange 是 "20-30" 这种字符串,这里拆成 salaryMin/salaryMax 两个数字
    setQueryParams(filters) {
      const [min, max] = filters.salaryRange
        ? filters.salaryRange.split('-')
        : ['', '']
      const { salaryRange, ...rest } = filters
      Object.assign(this.queryParams, {
        ...rest,
        salaryMin: min === '' ? null : Number(min),
        salaryMax: max === '' ? null : Number(max)
      })
    },

    // 查询职位列表
    async fetchJobList() {
      this.loading = true
      try {
        const res = await request.get('/jobs/page', { params: this.queryParams })
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

    // (已删除 recordClick)
    // 原逻辑:点职位详情就调 POST /jobs/applications/{id}/click 存 clicked 记录
    // 问题:会产生大量"点过但没投"的垃圾数据,污染求职进度列表
    // 改进:点击详情不再存记录;真正的投递行为才记录(submitted/interviewed/...)
  }
})
