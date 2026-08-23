/**
 * 注意:这里统一复用 @/utils/request(已配置 baseURL=/api、token 拦截器、
 * 统一错误处理和 res.data 拆壳),不再用原生 fetch。
 * 请求写法:           get('/agents/model-status')                → 实际请求 /api/agents/model-status
 */
import { get, post } from '@/utils/request'

/** 获取模型状态 */
export function getModelStatus() {
  return get('/agents/model-status')
}

/** 发送聊天消息 */
export function sendChatMessage({ message, session_id, industry, role }) {
  return post('/agents/chat', { message, session_id, industry, role })
}

/** 获取管理后台监控指标 */
export function getAdminMetrics() {
  return get('/v1/admin/metrics')
}

/** 获取追踪详情 */
export function getTraceDetail(traceId) {
  return get(`/v1/admin/traces/${traceId}`)
}

/** 获取告警数据 */
export function getAlerts() {
  return get('/v1/admin/alerts')
}
