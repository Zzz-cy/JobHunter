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
      page: 1,
      pageSize: 20
    },

    // 收藏的职位 id 集合
    favoriteIds: new Set()
  }),

  getters: {
    isFavorited: (state) => (jobId) => state.favoriteIds.has(jobId)
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
      // TODO: 调用后端接口
      // const res = await request.get(`/jobs/${id}`)
      // this.currentJob = res
      console.log('[TODO] fetchJobDetail', id)
    },

    // 收藏/取消收藏
    async toggleFavorite(jobId) {
      // TODO: 调用后端收藏接口
      // if (this.favoriteIds.has(jobId)) {
      //   await request.delete(`/applications/${jobId}/favorite`)
      //   this.favoriteIds.delete(jobId)
      // } else {
      //   await request.post(`/applications/${jobId}/favorite`)
      //   this.favoriteIds.add(jobId)
      // }
      console.log('[TODO] toggleFavorite', jobId)
    },

    // 记录跳转点击
    async recordClick(jobId) {
      // TODO: 调用后端记录点击事件
      // await request.post('/applications', { jobId, status: 'clicked' })
      console.log('[TODO] recordClick', jobId)
    },

    // 重置查询条件
    resetQuery() {
      this.queryParams = {
        keyword: '',
        city: '',
        salaryMin: null,
        salaryMax: null,
        experience: '',
        education: '',
        industry: '',
        source: '',
        page: 1,
        pageSize: 20
      }
    }
  }
})
