import { ref } from 'vue'
import { post, get } from '@/utils/request'

// ==================== 角色和行业配置 ====================
export const ROLE_QUICK_QUESTIONS = {
  job_seeker: [
    { label: '🔍 岗位分析', question: '这个岗位需要什么技能？' },
    { label: '📊 差距分析', question: '我的技能和目标岗位差什么？' },
    { label: '🎓 学习路径', question: '如何规划学习路径提升竞争力？' },
    { label: '📈 趋势预测', question: '未来哪些技能最吃香？' },
    { label: '📋 生成报告', question: '帮我出一份技能提升方案' },
    { label: '⚖️ 岗位对比', question: '这两个岗位哪个更适合我？' },
  ],
  hr: [
    { label: '🔍 岗位画像', question: '这个岗位的核心能力要求是什么？' },
    { label: '👥 人才评估', question: '如何评估候选人是否匹配岗位？' },
    { label: '📈 市场趋势', question: '当前人才市场趋势如何？' },
    { label: '📋 生成报告', question: '帮我出一份人才市场分析报告' },
    { label: '⚖️ 岗位对比', question: '不同级别的岗位要求有什么差异？' },
    { label: '🎯 招聘建议', question: '如何优化招聘策略？' },
  ],
  career_planner: [
    { label: '🧭 转行规划', question: '如何规划跨行业转型？' },
    { label: '📊 差距分析', question: '转型需要补充哪些技能？' },
    { label: '🎓 学习路径', question: '推荐什么学习路径？' },
    { label: '📜 认证路径', question: '需要考哪些证书？' },
    { label: '📈 行业前景', question: '目标行业前景如何？' },
    { label: '📋 综合规划', question: '帮我制定职业发展规划' },
  ],
  manager: [
    { label: '📊 团队分析', question: '团队当前技能矩阵如何？' },
    { label: '🎯 培训需求', question: '团队需要哪些培训？' },
    { label: '📈 行业对标', question: '行业标杆团队能力如何？' },
    { label: '📋 生成报告', question: '帮我出一份团队能力评估报告' },
    { label: '👥 人才规划', question: '如何规划人才梯队？' },
    { label: '⚖️ 对标分析', question: '与行业标杆差距在哪？' },
  ],
}

export const INDUSTRY_QUICK_QUESTIONS = {
  it: [
    { label: '🔍 岗位分析', question: 'Python后端开发需要什么技能？' },
    { label: '📊 差距分析', question: '我会Java，想转数据分析，差什么？' },
    { label: '🎓 学习路径', question: '如何从前端转全栈开发？' },
    { label: '📈 趋势预测', question: 'AI行业未来什么技能最重要？' },
    { label: '📋 生成报告', question: '帮我出一份数据分析行业报告' },
    { label: '⚖️ 岗位对比', question: '前端和后端的技能要求有什么不同？' },
  ],
  finance: [
    { label: '🔍 岗位分析', question: '基金经理需要什么资质和技能？' },
    { label: '📊 差距分析', question: '我有CPA，想转投行，还差什么？' },
    { label: '🎓 学习路径', question: '如何从银行柜员转岗风控分析师？' },
    { label: '📈 趋势预测', question: '金融科技未来需要什么技能？' },
    { label: '📋 生成报告', question: '帮我出一份金融行业人才趋势报告' },
    { label: '⚖️ 岗位对比', question: '投行和商业银行的技能要求有什么不同？' },
  ],
  healthcare: [
    { label: '🔍 岗位分析', question: '临床医师需要什么技能和资质？' },
    { label: '📊 差距分析', question: '我是护士，想转医院管理，差什么？' },
    { label: '🎓 学习路径', question: '如何从药师转岗临床研究？' },
    { label: '📈 趋势预测', question: '医疗AI未来需要什么人才？' },
    { label: '📋 生成报告', question: '帮我出一份医疗行业人才需求报告' },
    { label: '⚖️ 岗位对比', question: '内科和外科医师的能力要求有什么不同？' },
  ],
  manufacturing: [
    { label: '🔍 岗位分析', question: '质量工程师需要什么技能？' },
    { label: '📊 差距分析', question: '我会CNC操作，想转工艺工程师，差什么？' },
    { label: '🎓 学习路径', question: '如何从技术员成长为生产经理？' },
    { label: '📈 趋势预测', question: '智能制造未来需要什么技能？' },
    { label: '📋 生成报告', question: '帮我出一份制造业人才趋势报告' },
    { label: '⚖️ 岗位对比', question: '质量工程师和工艺工程师有什么不同？' },
  ],
  education: [
    { label: '🔍 岗位分析', question: '高中数学教师需要什么技能？' },
    { label: '📊 差距分析', question: '我是传统教师，想转在线教育，差什么？' },
    { label: '🎓 学习路径', question: '如何从助教成长为教授？' },
    { label: '📈 趋势预测', question: '教育科技未来需要什么人才？' },
    { label: '📋 生成报告', question: '帮我出一份教育行业人才趋势报告' },
    { label: '⚖️ 岗位对比', question: '公立学校和培训机构教师有什么不同？' },
  ],
}

export const ROLE_OPTIONS = [
  { value: 'job_seeker', label: '🎓 求职者' },
  { value: 'hr', label: '👔 HR' },
  { value: 'career_planner', label: '🧭 规划师' },
  { value: 'manager', label: '📊 管理者' },
]

export const INDUSTRY_OPTIONS = [
  { value: 'it', label: 'IT/互联网' },
  { value: 'finance', label: '金融' },
  { value: 'healthcare', label: '医疗/医药' },
  { value: 'manufacturing', label: '制造/工业' },
  { value: 'education', label: '教育' },
]

// ⭐ 会话状态提升到模块级(单例): 卡片跳 /jobs/:id 等路由切换会卸载 ChatView,
// 若 ref 建在 useChat() 内部则每次挂载都是全新空状态 → "跳走就回不到大模型/只剩欢迎语"。
// 模块级共享后, 组件卸载再回来(前进/后退导航)对话与 sessionId 原样保留; 整页刷新才重置(历史仍可开抽屉续聊)。
const messages = ref([])
const sessionId = ref(null)
const isProcessing = ref(false)
const modelStatus = ref('加载中...')
const sessions = ref([])         // 我的历史会话列表(用于续聊)

// ⭐ 归属用户守卫: 模块级状态是跨组件/跨路由共享的, 若登录人变了必须清空,
// 否则"登出→换账号登录(同一tab不刷新)"会看到上一个账号残留的对话/历史(隐私+串号 bug)。
// 用哨兵标记"尚未绑定任何用户", 首次进入也算一次绑定。
let chatOwnerId = Symbol('unset')   // 当前这份会话属于哪个 user_id(null=匿名)

export function useChat() {

  // 账号切换时清空当前对话与会话列表(保留会话本身在库里, 新账号可开抽屉看自己的)
  function syncChatOwner(uid) {
    if (chatOwnerId !== uid) {
      chatOwnerId = uid
      sessionId.value = null
      messages.value = []
      sessions.value = []
      isProcessing.value = false
    }
  }

  async function loadModelStatus() {
    // 厂商 provider 值 → 中文展示名(与 llm_module config 里 provider_label 对齐)
    const PROVIDER_LABELS = {
      zhipu: '智谱',
      deepseek: 'DeepSeek',
      kimi: 'Kimi(Moonshot)',
      dashscope: '通义千问(阿里)',
      xfyun: '讯飞星火',
    }
    try {
      const data = await get('/agents/model-status')
      const text = `${PROVIDER_LABELS[data.provider] || data.provider || '智谱'} ${data.model}`
      modelStatus.value = text
    } catch {
      modelStatus.value = '智谱 GLM-4'
    }
  }

  // 拉取当前登录用户的历史会话列表(登录后才有;接口只回本人+匿名会话)
  async function listSessions() {
    try {
      const data = await get('/agents/sessions')
      sessions.value = (data && data.sessions) || []
    } catch {
      sessions.value = []
    }
  }

  // 打开某历史会话: 拉完整消息回放, 并把 sessionId 定为它 → 下一条即续聊
  async function openSession(id) {
    try {
      const data = await get(`/agents/sessions/${id}/messages`)
      sessionId.value = id
      messages.value = (data && data.messages || []).map((m) => {
        const isUser = m.role === 'user'
        const base = { id: m.id, intent: m.intent || null }
        return isUser
          ? { role: 'user', content: m.content, ...base }
          // ⭐ 历史回放带当年真实岗位卡片(assistant 消息落库的 recommended_jobs 列):
          //   前端据此重渲染卡片 → 旧推荐可再次点击跳详情
          : { role: 'bot', answer: m.content, recommended_jobs: m.recommended_jobs || [], ...base }
      })
    } catch (err) {
      messages.value.push({ role: 'error', content: err.message })
    }
  }

  // 清空当前对话(开新会话); 历史仍留在库中可续
  function newChat() {
    sessionId.value = null
    messages.value = []
    addWelcomeMessage()
  }

  async function sendMessage(text, industry, role, context) {
    if (!text || isProcessing.value) return

    const userMsg = { role: 'user', content: text }
    messages.value.push(userMsg)
    isProcessing.value = true

    try {
      // context: 主站"问顾问"入口带岗位上下文, 形如 { job_id: 6320 }
      const body = {
        message: text,
        session_id: sessionId.value,
        industry,
        role,
      }
      if (context && Object.keys(context).length) {
        body.context = context
      }
      const result = await post('/agents/chat', body, {
        timeout: 300000,  // 多Agent/长生成(简历匹配/趋势报告)可能跑1-3分钟,放宽到300秒(对齐后端与nginx)
      })

      if (result.session_id) {
        sessionId.value = result.session_id
      }

      messages.value.push({ role: 'bot', ...result })
    } catch (err) {
      messages.value.push({ role: 'error', content: err.message })
    } finally {
      isProcessing.value = false
    }
  }

  function addWelcomeMessage() {
    const modelName = modelStatus.value || '智谱 GLM-4'
    messages.value.push({
      role: 'bot',
      answer: `你好！我是**岗能智绘**的智能助手。\n\n我可以帮你：\n• 分析岗位技能要求\n• 评估能力差距\n• 规划学习路径\n• 预测行业趋势\n• 生成分析报告\n\n当前使用模型：**${modelName}** | 支持自动降级`,
      intent: null,
      tasks: [],
    })
  }

  return {
    messages,
    sessionId,
    isProcessing,
    modelStatus,
    sessions,
    loadModelStatus,
    listSessions,
    openSession,
    newChat,
    sendMessage,
    addWelcomeMessage,
    syncChatOwner,
  }
}
