import { defineStore } from 'pinia'
// import request from '@/utils/request'

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
      // TODO: 调用后端接口
      // const res = await request.get('/resumes')
      // this.resumeList = res.list
      console.log('[TODO] fetchResumeList')
    },

    // 上传简历文件
    async uploadResume(file) {
      this.uploadStatus = 'uploading'
      this.parseError = ''
      // TODO: 上传文件并触发解析
      // const formData = new FormData()
      // formData.append('file', file)
      // try {
      //   const res = await request.post('/resumes/upload', formData, {
      //     headers: { 'Content-Type': 'multipart/form-data' },
      //     onUploadProgress: (e) => {
      //       this.parseProgress = Math.round((e.loaded * 100) / e.total)
      //     }
      //   })
      //   this.uploadStatus = 'parsing'
      //   // 轮询解析状态
      //   await this.pollParseStatus(res.id)
      // } catch (err) {
      //   this.uploadStatus = 'failed'
      //   this.parseError = err.message
      // }
      console.log('[TODO] uploadResume', file.name)
    },

    // 轮询解析状态
    async pollParseStatus(resumeId) {
      // TODO: 轮询简历解析状态直到 done/failed
      // while (true) {
      //   await new Promise((r) => setTimeout(r, 2000))
      //   const res = await request.get(`/resumes/${resumeId}/status`)
      //   if (res.parseStatus === 'done') {
      //     this.uploadStatus = 'done'
      //     await this.fetchResumeList()
      //     break
      //   }
      //   if (res.parseStatus === 'failed') {
      //     this.uploadStatus = 'failed'
      //     this.parseError = res.parseError
      //     break
      //   }
      // }
      console.log('[TODO] pollParseStatus', resumeId)
    },

    // 删除简历
    async deleteResume(id) {
      // TODO: 调用后端删除接口
      // await request.delete(`/resumes/${id}`)
      // await this.fetchResumeList()
      console.log('[TODO] deleteResume', id)
    },

    // 获取推荐结果
    async fetchRecommendations(resumeId) {
      // TODO: 调用后端推荐接口
      // const res = await request.get(`/recommendations?resumeId=${resumeId}`)
      // return res.list
      console.log('[TODO] fetchRecommendations', resumeId)
      return []
    }
  }
})
