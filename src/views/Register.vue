<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
    </div>

    <div class="auth-card">
      <div class="auth-header">
        <el-icon :size="36" color="#409eff"><Promotion /></el-icon>
        <h1>创建账号</h1>
        <p>加入 JobHunter,让 AI 帮你找工作</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent
      >
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="form.phone"
            placeholder="请输入手机号"
            :prefix-icon="Iphone"
            maxlength="11"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱"
            :prefix-icon="Message"
            maxlength="50"
          />
        </el-form-item>

        <el-form-item label="昵称" prop="nickname">
          <el-input
            v-model="form.nickname"
            placeholder="给自己起个昵称(选填)"
            :prefix-icon="User"
            maxlength="20"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="6-20位字符"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item prop="agree">
          <el-checkbox v-model="form.agree">
            我已阅读并同意
            <el-link type="primary" :underline="false">《用户协议》</el-link>
            <el-link type="primary" :underline="false">《隐私政策》</el-link>
          </el-checkbox>
        </el-form-item>

        <el-button
          type="primary"
          class="auth-submit"
          :loading="loading"
          @click="handleSubmit"
        >
          注册
        </el-button>

        <div class="auth-footer">
          已有账号?
          <el-link type="primary" :underline="false" @click="goLogin">
            去登录
          </el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Iphone, Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  phone: '',
  email: '',
  nickname: '',
  password: '',
  confirmPassword: '',
  agree: false
})

const validatePass2 = (_rule, value, callback) => {
  if (value !== form.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const validateAgree = (_rule, value, callback) => {
  if (!value) callback(new Error('请先同意用户协议'))
  else callback()
}

const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  nickname: [
    { min: 2, max: 20, message: '昵称 2-20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码 6-20 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePass2, trigger: 'blur' }
  ],
  agree: [{ validator: validateAgree, trigger: 'change' }]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    loading.value = true
    await userStore.register({
      phone: form.phone,
      email: form.email,
      nickname: form.nickname || undefined,
      password: form.password
    })
    ElMessage.success('注册成功,请登录')
    router.push('/login')
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const goLogin = () => router.push('/login')
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
  padding: 40px 0;
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
  margin-bottom: 24px;
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

.auth-submit {
  width: 100%;
  margin-top: 8px;
}

.auth-footer {
  text-align: center;
  color: #606266;
  font-size: 13px;
  margin-top: 16px;
}
</style>
