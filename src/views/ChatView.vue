<template>
  <div class="chat-container">
    <ChatHeader
      :model-status="modelStatus"
      v-model:role="currentRole"
      v-model:industry="currentIndustry"
      @update:role="onRoleChange"
      @update:industry="onIndustryChange"
    />

    <!-- 会话工具栏: 历史会话入口 + 岗位咨询状态 + 新对话 -->
    <div class="chat-toolbar">
      <div class="toolbar-left">
        <button class="tool-btn" @click="openHistory">🕘 历史会话</button>
        <span v-if="askJobId" class="job-ask-chip">
          🎯 正在咨询岗位 #{{ askJobId }}
          <em class="job-ask-end" @click="exitJobAsk">✕ 结束咨询</em>
        </span>
      </div>
      <div class="toolbar-right">
        <button class="tool-btn" @click="startNewChat">➕ 新对话</button>
      </div>
    </div>

    <QuickQuestions :questions="questions" @select="onQuickSelect" />

    <ChatArea :messages="messages" :is-processing="isProcessing" />

    <InputArea :disabled="isProcessing" @send="onSend" />

    <!-- 历史会话抽屉 -->
    <el-drawer
      v-model="historyOpen"
      title="历史会话"
      size="340px"
      :append-to-body="true"
    >
      <div class="session-panel">
        <div v-if="!sessions.length" class="session-empty">
          <div class="session-empty-icon">🗂️</div>
          <div>暂无历史会话</div>
          <div class="session-empty-sub">提问后会话会自动保存，刷新页面也不会丢失</div>
        </div>
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="resumeSession(s)"
        >
          <div class="session-row">
            <span class="session-title">会话 · {{ s.id }}</span>
            <span class="session-count">{{ s.message_count }} 条</span>
          </div>
          <div class="session-meta">{{ fmtSessionTime(s.created_at) }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import '@/styles/chat.css'
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useChat, ROLE_QUICK_QUESTIONS, INDUSTRY_QUICK_QUESTIONS } from '@/composables/useChat'
import ChatHeader from '@/components/chat/ChatHeader.vue'
import QuickQuestions from '@/components/chat/QuickQuestions.vue'
import ChatArea from '@/components/chat/ChatArea.vue'
import InputArea from '@/components/chat/InputArea.vue'

const route = useRoute()
const userStore = useUserStore()

const {
  messages, sessionId, isProcessing, modelStatus, sessions,
  loadModelStatus, listSessions, openSession, newChat, sendMessage, addWelcomeMessage, syncChatOwner,
} = useChat()

const currentRole = ref('job_seeker')
const currentIndustry = ref('it')
const questions = ref(ROLE_QUICK_QUESTIONS['job_seeker'])
const historyOpen = ref(false)
const askJobId = ref(null)   // 主站"问顾问"入口: 非空则每轮都带 context:{job_id}

function updateQuestions() {
  const roleQs = ROLE_QUICK_QUESTIONS[currentRole.value]
  const industryQs = INDUSTRY_QUICK_QUESTIONS[currentIndustry.value]
  questions.value = roleQs || industryQs || INDUSTRY_QUICK_QUESTIONS['it']
}

function onRoleChange(val) {
  currentRole.value = val
  updateQuestions()
}

function onIndustryChange(val) {
  currentIndustry.value = val
  updateQuestions()
}

function onQuickSelect(question) {
  onSend(question)
}

// 发消息: 处于"岗位咨询"模式时, 每轮都带 context:{job_id}, 让顾问始终针对这条JD
function onSend(text) {
  const context = askJobId.value ? { job_id: Number(askJobId.value) } : undefined
  sendMessage(text, currentIndustry.value, currentRole.value, context)
}

// 历史会话: 打开抽屉时刷新列表
async function openHistory() {
  await listSessions()
  historyOpen.value = true
}

function resumeSession(s) {
  historyOpen.value = false
  askJobId.value = null          // 切到历史会话 = 退出岗位咨询模式
  openSession(s.id)
}

function startNewChat() {
  askJobId.value = null
  newChat()
  updateQuestions()
}

function exitJobAsk() {
  askJobId.value = null
}

// 岗位详情页"问顾问"进入: ?job=xxx(带登录) → 清屏后直接针对该岗位提问
async function askForJob(jid) {
  askJobId.value = String(jid)
  messages.value = []
  sessionId.value = null
  updateQuestions()
  await sendMessage(
    '请结合我的简历分析这个岗位：它具体做什么、要求哪些技能、我和它的匹配度如何、差距在哪里，以及我是否适合投递。',
    currentIndustry.value,
    currentRole.value,
    { job_id: Number(jid) },
  )
}

const fmtSessionTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 当前登录用户的 id(未登录/匿名 = null)。聊天归属用它判断: 登录人变了 → 清空上一个账号的残留会话
const currentUserId = () => (userStore.isLoggedIn ? (userStore.userInfo?.id ?? null) : null)

onMounted(async () => {
  // ⭐ 账号守卫: 同 tab 换账号登录后进入顾问页, 先清掉上一账号的对话/历史, 再走正常欢迎/续聊
  syncChatOwner(currentUserId())
  await loadModelStatus()
  const jid = route.query.job || route.query.ask_job
  if (jid) {
    await askForJob(jid)
    // 清掉 query,避免刷新页面又自动重问一次
    window.history.replaceState({}, '', '/recommend')
  } else if (!messages.value.length) {
    // ⭐ 会话状态是模块级共享的: 从卡片跳岗位详情再"返回 AI 顾问"回来时,
    // messages 仍保留原对话 → 只在真空对话时补欢迎语, 避免覆盖/重复
    addWelcomeMessage()
  }
  updateQuestions()
  listSessions()   // 预载历史会话数(失败静默)
})

// 组件还挂着时登入/登出/换账号(如顶栏登录后跳回本页) → 也按新账号重置会话
watch(
  () => (userStore.isLoggedIn ? userStore.userInfo?.id : null),
  (uid, prev) => {
    if (prev !== undefined && uid !== prev) {
      syncChatOwner(uid ?? null)
    }
  }
)

// 已在对话页时又点别处的"问顾问"?: 变化才触发
watch(() => route.query.job, (jid) => {
  if (jid && String(jid) !== askJobId.value) {
    askForJob(jid)
  }
})
</script>

<style scoped>
.chat-container {
  width: 100%;
  max-width: 900px;
  height: calc(100vh - 64px);
  margin: 0 auto;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  /* ⭐ 新增:阴影 + 圆角,和灰色背景拉开层次 */
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
}

/* 会话工具栏 */
.chat-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 18px;
  background: #fbfbff;
  border-bottom: 1px solid #eef0f6;
  flex-shrink: 0;
}
.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tool-btn {
  border: 1px solid #dde1f5;
  background: #fff;
  color: #4a5578;
  font-size: 13px;
  padding: 5px 12px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.tool-btn:hover {
  border-color: #667eea;
  color: #667eea;
}
.job-ask-chip {
  font-size: 13px;
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fce7a5;
  padding: 5px 12px;
  border-radius: 16px;
}
.job-ask-end {
  font-style: normal;
  margin-left: 6px;
  cursor: pointer;
  opacity: 0.7;
}
.job-ask-end:hover { opacity: 1; }

/* 历史会话抽屉 */
.session-panel { padding: 0 2px; }
.session-empty {
  text-align: center;
  color: #909399;
  font-size: 14px;
  padding: 48px 0;
}
.session-empty-icon { font-size: 40px; margin-bottom: 12px; }
.session-empty-sub { font-size: 12px; color: #c0c4cc; margin-top: 8px; line-height: 1.6; }

.session-item {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #eef0f6;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}
.session-item:hover { border-color: #667eea; }
.session-item.active {
  border-color: #667eea;
  background: #f2f4ff;
}
.session-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.session-title { font-size: 14px; font-weight: 600; color: #303133; }
.session-count { font-size: 12px; color: #667eea; background: #f0f2ff; padding: 1px 8px; border-radius: 10px; }
.session-meta { font-size: 12px; color: #a0a6bd; margin-top: 6px; }

@media (max-width: 768px) {
  .chat-container {
    border-radius: 0;
    max-width: 100%;
  }
}
</style>
