import { defineStore } from 'pinia'
// import request from '@/utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null')
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.nickname || state.userInfo?.phone || ''
  },

  actions: {
    // 登录
    async login(payload) {
      // TODO: 调用后端登录接口
      // const res = await request.post('/auth/login', payload)
      // this.token = res.token
      // this.userInfo = res.user
      // localStorage.setItem('token', this.token)
      // localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
      console.log('[TODO] login', payload)
    },

    // 注册
    async register(payload) {
      // TODO: 调用后端注册接口
      // const res = await request.post('/auth/register', payload)
      // return res
      console.log('[TODO] register', payload)
    },

    // 退出登录
    async logout() {
      // TODO: 可调用后端登出接口
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },

    // 获取当前用户信息
    async fetchUserInfo() {
      // TODO: 调用后端获取用户信息
      // const res = await request.get('/user/me')
      // this.userInfo = res
      // localStorage.setItem('userInfo', JSON.stringify(res))
    }
  }
})
