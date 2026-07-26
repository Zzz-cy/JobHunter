<template>
  <div class="input-area">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        class="input-field"
        v-model="text"
        placeholder="输入你的职业相关问题..."
        rows="1"
        @keydown="onKeydown"
        @input="autoResize"
      ></textarea>
    </div>
    <button class="send-btn" :disabled="disabled || !text.trim()" @click="send">
      ➤
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['send'])
defineProps({ disabled: { type: Boolean, default: false } })

const text = ref('')
const textareaRef = ref(null)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function send() {
  const msg = text.value.trim()
  if (!msg) return
  emit('send', msg)
  text.value = ''
  autoResize()
}
</script>

<style scoped>
.input-area {
  padding: 15px 30px;
  background: white;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-shrink: 0;
}

.input-wrapper {
  flex: 1;
  position: relative;
}

.input-field {
  width: 100%;
  padding: 12px 18px;
  border: 2px solid #e9ecef;
  border-radius: 24px;
  font-size: 14px;
  outline: none;
  resize: none;
  min-height: 48px;
  max-height: 120px;
  font-family: inherit;
  transition: border-color 0.2s;
}

.input-field:focus { border-color: #667eea; }
.input-field::placeholder { color: #adb5bd; }

.send-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 768px) {
  .input-area { padding: 10px 20px; }
}
</style>
