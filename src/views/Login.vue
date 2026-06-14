<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>

    <div class="auth-card">
      <div class="auth-header">
        <el-icon :size="36" color="#409eff"><Promotion /></el-icon>
        <h1>欢迎回来</h1>
        <p>登录 JobHunter 开启智能求职之旅</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent
      >
        <el-form-item label="账号" prop="account">
          <el-input
            v-model="form.account"
            placeholder="手机号 / 邮箱"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            :prefix-icon="Lock"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <div class="auth-options">
          <el-checkbox v-model="form.remember">记住我</el-checkbox>
          <el-link type="primary" :underline="false">忘记密码?</el-link>
        </div>

        <el-button
          type="primary"
          class="auth-submit"
          :loading="loading"
          @click="handleSubmit"
        >
          登录
        </el-button>

        <div class="auth-divider">
          <el-divider>其他登录方式</el-divider>
        </div>

        <div class="auth-third">
          <el-button circle :icon="Chat" />
          <el-button circle :icon="Message" />
          <el-button circle :icon="Iphone" />
        </div>

        <div class="auth-footer">
          还没有账号?
          <el-link type="primary" :underline="false" @click="goRegister">
            立即注册
          </el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock, Chat, Message, Iphone } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
// import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
// const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  account: '',
  password: '',
  remember: false
})

const rules = {
  account: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 3, message: '账号至少 3 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    loading.value = true
    // TODO: 调用 store 登录接口
    // await userStore.login({
    //   account: form.account,
    //   password: form.password,
    //   remember: form.remember
    // })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/home'
    router.push(redirect)
  } catch (err) {
    if (err?.message) ElMessage.error(err.message)
  } finally {
    loading.value = false
  }
}

const goRegister = () => router.push('/register')
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.auth-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.bg-circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  left: -100px;
}

.bg-circle-2 {
  width: 300px;
  height: 300px;
  bottom: -80px;
  right: -80px;
}

.bg-circle-3 {
  width: 200px;
  height: 200px;
  top: 50%;
  right: 10%;
}

.auth-card {
  width: 420px;
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  z-index: 1;
}

.auth-header {
  text-align: center;
  margin-bottom: 28px;
}

.auth-header h1 {
  font-size: 24px;
  color: #303133;
  margin: 12px 0 6px;
}

.auth-header p {
  color: #909399;
  font-size: 13px;
}

.auth-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.auth-submit {
  width: 100%;
}

.auth-divider {
  margin: 24px 0;
}

.auth-third {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 20px;
}

.auth-footer {
  text-align: center;
  color: #606266;
  font-size: 13px;
}
</style>
