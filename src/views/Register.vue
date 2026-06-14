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

        <el-form-item label="验证码" prop="code">
          <div class="code-row">
            <el-input
              v-model="form.code"
              placeholder="请输入短信验证码"
              :prefix-icon="Key"
              maxlength="6"
            />
            <el-button
              type="primary"
              plain
              :disabled="counting > 0"
              @click="sendCode"
            >
              {{ counting > 0 ? `${counting}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="昵称" prop="nickname">
          <el-input
            v-model="form.nickname"
            placeholder="给自己起个昵称"
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
import { User, Lock, Iphone, Key } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
// import { useUserStore } from '@/stores/user'
// import request from '@/utils/request'

const router = useRouter()
// const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const counting = ref(0)

const form = reactive({
  phone: '',
  code: '',
  nickname: '',
  password: '',
  confirmPassword: '',
  agree: false
})

const validatePass2 = (rule, value, callback) => {
  if (value !== form.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const validateAgree = (rule, value, callback) => {
  if (!value) callback(new Error('请先同意用户协议'))
  else callback()
}

const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位', trigger: 'blur' }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
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

const sendCode = async () => {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  // TODO: 调用后端发送验证码
  // await request.post('/auth/send-code', { phone: form.phone })
  ElMessage.success('验证码已发送')
  counting.value = 60
  const timer = setInterval(() => {
    counting.value--
    if (counting.value <= 0) clearInterval(timer)
  }, 1000)
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    loading.value = true
    // TODO: 调用 store 注册接口
    // await userStore.register({
    //   phone: form.phone,
    //   code: form.code,
    //   nickname: form.nickname,
    //   password: form.password
    // })
    ElMessage.success('注册成功,请登录')
    router.push('/login')
  } catch (err) {
    if (err?.message) ElMessage.error(err.message)
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

.code-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.code-row .el-input {
  flex: 1;
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
