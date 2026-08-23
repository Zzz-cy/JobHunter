<template>
  <div class="chat-container">
    <ChatHeader
      :model-status="modelStatus"
      v-model:role="currentRole"
      v-model:industry="currentIndustry"
      @update:role="onRoleChange"
      @update:industry="onIndustryChange"
    />

    <QuickQuestions :questions="questions" @select="onQuickSelect" />

    <ChatArea :messages="messages" :is-processing="isProcessing" />

    <InputArea :disabled="isProcessing" @send="onSend" />
  </div>
</template>

<script setup>
import '@/styles/chat.css'
import { ref, onMounted } from 'vue'
import { useChat, ROLE_QUICK_QUESTIONS, INDUSTRY_QUICK_QUESTIONS, ROLE_OPTIONS, INDUSTRY_OPTIONS } from '@/composables/useChat'
import ChatHeader from '@/components/chat/ChatHeader.vue'
import QuickQuestions from '@/components/chat/QuickQuestions.vue'
import ChatArea from '@/components/chat/ChatArea.vue'
import InputArea from '@/components/chat/InputArea.vue'

const {
  messages, isProcessing, modelStatus,
  loadModelStatus, sendMessage, addWelcomeMessage,
} = useChat()

const currentRole = ref('job_seeker')
const currentIndustry = ref('it')
const questions = ref(ROLE_QUICK_QUESTIONS['job_seeker'])

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

function onSend(text) {
  sendMessage(text, currentIndustry.value, currentRole.value)
}

onMounted(async () => {
  await loadModelStatus()
  addWelcomeMessage()
  updateQuestions()
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

@media (max-width: 768px) {
  .chat-container {
    border-radius: 0;
    max-width: 100%;
  }
}
</style>
