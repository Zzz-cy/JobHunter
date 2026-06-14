import axios from 'axios'
import { ElMessage } from 'element-plus'

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
    // TODO: 从 localStorage 或 user store 读取 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器:统一错误处理
request.interceptors.response.use(
  (response) => {
    const res = response.data
    // TODO: 根据后端实际返回结构判断成功/失败
    // if (res.code !== 0) {
    //   ElMessage.error(res.message || '请求失败')
    //   return Promise.reject(new Error(res.message || 'Error'))
    // }
    return res
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络异常'
    ElMessage.error(message)

    // 401 未登录或登录过期
    if (error.response?.status === 401) {
      // TODO: 清除登录信息,跳转登录页
      // localStorage.removeItem('token')
      // router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request
