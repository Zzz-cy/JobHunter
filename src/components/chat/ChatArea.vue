<template>
  <div class="chat-area" ref="chatRef">
    <template v-for="(msg, i) in messages" :key="i">
      <!-- 用户消息 -->
      <div v-if="msg.role === 'user'" class="message user">
        <div class="avatar">👤</div>
        <div class="message-content">{{ msg.content }}</div>
      </div>

      <!-- 机器人消息 -->
      <MessageBubble v-else-if="msg.role === 'bot'" :msg="msg" />

      <!-- 错误消息 -->
      <div v-else-if="msg.role === 'error'" class="message bot">
        <div class="avatar">⚠️</div>
        <div class="message-content error-msg">
          <div style="font-weight:600;">请求失败</div>
          <div style="margin-top:4px; font-size:13px;">{{ msg.content }}</div>
          <div style="margin-top:8px; font-size:12px; color:#666;">
            请检查：<br>1. 后端服务是否已启动 (docker compose up -d --build backend)<br>
            2. API地址是否正确<br>
            3. 网络连接是否正常
          </div>
        </div>
      </div>
    </template>

    <!-- 加载动画 -->
    <div v-if="isProcessing" class="message bot">
      <div class="avatar">🤖</div>
      <div class="message-content">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isProcessing: { type: Boolean, default: false },
})

const chatRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

watch(
  () => props.messages.length,
  scrollToBottom
)
watch(() => props.isProcessing, scrollToBottom)
</script>

<style scoped>
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px 30px;
  background: #f5f7fa;
}

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

.message.user { flex-direction: row-reverse; }

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.message.bot .avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.message.user .avatar { background: #e9ecef; }

.message-content {
  max-width: 70%;
  padding: 12px 18px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
}

.message.bot .message-content {
  background: white;
  color: #333;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border-top-left-radius: 4px;
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-top-right-radius: 4px;
}

.error-msg {
  background: #ffebee !important;
  color: #c62828 !important;
  border-top-left-radius: 18px !important;
}

.loading-dots {
  display: flex;
  gap: 4px;
  padding: 12px 18px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #667eea;
  animation: bounce 1.4s ease-in-out infinite both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

@media (max-width: 768px) {
  .chat-area { padding: 15px 20px; }
  .message-content { max-width: 85%; }
}
</style>
