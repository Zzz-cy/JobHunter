import { defineStore } from 'pinia'
import request from '@/utils/request'

// 安全读取 localStorage 中的 JSON,解析失败返回 null(避免污染数据让整站崩)
const safeReadJSON = (key) => {
  try {
    const raw = localStorage.getItem(key)
    const parsed = raw ? JSON.parse(raw) : null
    // 过滤掉 "undefined" / "null" 这类异常值
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    // 存的是脏数据(如字符串 "undefined"),清掉避免下次还崩
    localStorage.removeItem(key)
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: safeReadJSON('userInfo')
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.nickname || state.userInfo?.phone || '',
    // 是否管理员: role === 'admin' 才能看到"数据管理"/"监控后台"菜单
    // 未登录或普通用户都返回 false
    isAdmin: (state) => state.userInfo?.role === 'admin'
  },

  actions: {
    // 登录
    async login(payload) {
      const res = await request.post('/auth/login', payload)
      this.token = res.token
      this.userInfo = res.user || null
      localStorage.setItem('token', this.token)
      // 只在拿到真实 user 对象时才存,避免写入 "undefined" 脏数据
      if (this.userInfo) {
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
      } else {
        localStorage.removeItem('userInfo')
      }
    },

    // 注册
    async register(payload) {
      const res = await request.post('/auth/register', payload)
      return res
    },

    // 退出登录
    async logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },

    // 获取当前用户信息
    async fetchUserInfo() {
      const res = await request.get('/user/me')
      this.userInfo = res
      localStorage.setItem('userInfo', JSON.stringify(res))
    }
  }
})
