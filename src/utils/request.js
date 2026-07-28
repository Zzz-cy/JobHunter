import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from  '@/stores/user.js'
import router from '@/router'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器:自动带 token
request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.isLoggedIn) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器:统一错误处理
request.interceptors.response.use(
  (response) => {
    const res = response.data
    // 兼容 LLM 服务的裸数据接口(没有 code/message/data 外壳)
    // 如 /agents/chat 直接返回 {answer, intent, tasks, session_id}
    if (res && typeof res === 'object' && !('code' in res)) {
      return res
    }
    // JobHunter 业务接口:统一 {code, message, data} 结构
    if (res.code !== 0) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || 'Error'))
    }
    // 后端统一返回结构 {code, message, data}
    // 业务代码只关心 data,这里拆掉外壳,让调用方直接拿到业务数据
    return res.data
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络异常'
    ElMessage.error(message)

    // 401 未登录或登录过期
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request

// 具名导出:兼容 import { get, post } from '@/utils/request' 写法
export const get = (url, config) => request.get(url, config)
export const post = (url, data, config) => request.post(url, data, config)
export const put = (url, data, config) => request.put(url, data, config)
export const del = (url, config) => request.delete(url, config)
