<template>
  <div class="message bot">
    <div class="avatar">🤖</div>
    <div>
      <div class="message-content" v-html="formattedAnswer"></div>
      <AgentTags v-if="msg.tasks && msg.tasks.length" :tasks="msg.tasks" />
      <ThinkingProcess v-if="msg.intent && msg.intent.intent" :intent="msg.intent" :tasks="msg.tasks" />
      <!-- 结构化岗位卡片:回答旁路附带(推荐/匹配),点击可跳岗位详情 -->
      <RecommendedJobs v-if="recommendedJobs.length" :jobs="recommendedJobs" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AgentTags from './AgentTags.vue'
import ThinkingProcess from './ThinkingProcess.vue'
import RecommendedJobs from './RecommendedJobs.vue'

const props = defineProps({
  msg: { type: Object, required: true },
})

const recommendedJobs = computed(() => (props.msg.recommended_jobs || []).slice(0, 6))

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

const formattedAnswer = computed(() => {
  let text = ''
  if (typeof props.msg.answer === 'string') {
    text = props.msg.answer
  } else if (props.msg.answer) {
    text = JSON.stringify(props.msg.answer, null, 2)
  } else {
    text = '收到回复，但格式异常'
  }

  return escapeHtml(text)
    .replace(/^### (.+)$/gm, '<h4 style="margin:10px 0 5px;font-size:14px;font-weight:600;">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:12px 0 6px;font-size:15px;font-weight:600;">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin:14px 0 8px;font-size:16px;font-weight:600;">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:12px;">$1</code>')
    .replace(/\n/g, '<br>')
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: fadeInUp 0.3s ease;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message-content {
  max-width: 70%;
  padding: 12px 18px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  background: white;
  color: #333;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border-top-left-radius: 4px;
}
</style>
