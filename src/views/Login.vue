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
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  account: '',
  password: '',
  remember: false
})

// 进入登录页时,如果之前勾过"记住我",自动回填账号并保持勾选
const savedAccount = localStorage.getItem('rememberAccount')
if (savedAccount) {
  form.account = savedAccount
  form.remember = true
}

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

    // 1. 登录拿 token
    await userStore.login({
      account: form.account,
      password: form.password
    })

    // 2. 拉最新用户信息(登录接口返回的 user 字段可能不全,这里以 /user/me 为准)
    await userStore.fetchUserInfo()

    // 3. 处理"记住账号"(纯前端偏好,不发后端)
    if (form.remember) {
      localStorage.setItem('rememberAccount', form.account)
    } else {
      localStorage.removeItem('rememberAccount')
    }

    // 4. 跳转
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/home'
    router.push(redirect)
  } catch (err) {
    console.error(err)
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

.auth-footer {
  text-align: center;
  color: #606266;
  font-size: 13px;
}
</style>
