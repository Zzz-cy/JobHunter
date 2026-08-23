import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useResumeStore = defineStore('resume', {
  state: () => ({
    // 用户的简历列表
    resumeList: [],

    // 当前选中的简历
    currentResume: null,

    // 上传解析进度
    uploadStatus: 'idle', // idle | uploading | parsing | done | failed
    parseProgress: 0,
    parseError: ''
  }),

  getters: {
    hasResume: (state) => state.resumeList.length > 0,
    parseStatusText: (state) => {
      const map = {
        idle: '等待上传',
        uploading: '上传中...',
        parsing: '解析中...',
        done: '解析完成',
        failed: '解析失败'
      }
      return map[state.uploadStatus] || ''
    }
  },

  actions: {
    // 获取简历列表
    async fetchResumeList() {
      const res = await request.get('/resumes/all')
      this.resumeList = res
    },

    // 上传简历文件
    async uploadResume(file, title) {
      this.uploadStatus = 'uploading'
      this.parseError = ''
      const formData = new FormData()
      formData.append('file', file)
      if (title) formData.append('title', title)
      try {
        // 上传 + 同步解析(后端会等 LLM 返回, 可能要 30-60 秒)
        // 单独配 120 秒超时(和后端 LLM_PARSE_TIMEOUT 对齐), 不用全局的 30 秒
        const res = await request.post('/resumes/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 120000,   // 2 分钟, AI 解析慢
          onUploadProgress: (e) => {
            this.parseProgress = Math.round((e.loaded * 100) / e.total)
          }
        })
        // 后端同步返回: 上传完解析也完了, 直接看 status
        if (res.parse_status === 'done') {
          this.uploadStatus = 'done'
        } else if (res.parse_status === 'failed') {
          this.uploadStatus = 'failed'
          this.parseError = res.parse_error || '简历解析失败, 可重试'
        } else {
          this.uploadStatus = 'done'
        }
      } catch (err) {
        this.uploadStatus = 'failed'
        this.parseError = err.message
      }
    }
  }
})
