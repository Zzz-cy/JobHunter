<template>
  <div class="onboarding-page">
    <div class="auth-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>

    <!-- 登错号时的唯一出口: 退出回登录页换号(不是跳过, 退出后仍进不了系统) -->
    <el-button class="logout-btn" text @click="handleLogout">
      <el-icon><SwitchButton /></el-icon>
      <span>退出登录</span>
    </el-button>

    <div class="onboarding-card">
      <div class="onboarding-header">
        <el-icon :size="36" color="#409eff"><Promotion /></el-icon>
        <h1>完善你的求职期望</h1>
        <p>填好三项, 立刻看到符合期望的岗位</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent
      >
        <el-form-item label="期望城市" prop="expectedCity">
          <el-select v-model="form.expectedCity" placeholder="选择期望城市" style="width: 100%">
            <el-option v-for="c in cityOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>

        <el-form-item label="期望职位" prop="expectedJob">
          <el-input
            v-model="form.expectedJob"
            placeholder="如: Python 后端工程师"
            maxlength="50"
            show-word-limit
          />
          <div v-if="hotKeywords.length" class="hot-tags">
            <span class="hot-tags-label">热门职位:</span>
            <el-check-tag
              v-for="kw in hotKeywords"
              :key="kw"
              :checked="form.expectedJob === kw"
              @change="selectHot(kw)"
            >
              {{ kw }}
            </el-check-tag>
          </div>
        </el-form-item>

        <el-form-item label="期望薪资" prop="expectedSalary">
          <el-select v-model="form.expectedSalary" placeholder="选择薪资档位" style="width: 100%">
            <el-option v-for="s in salaryOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>

        <el-button
          type="primary"
          class="onboarding-submit"
          :loading="loading"
          @click="handleSubmit"
        >
          进入 JobHunter
        </el-button>

        <p class="onboarding-tip">三项均为必填, 建档后为你打开匹配的岗位列表</p>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Promotion, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { useJobStore } from '@/stores/job'
import { cityOptions, salaryOptions } from '@/constants/filterOptions'

const router = useRouter()
const userStore = useUserStore()
const jobStore = useJobStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  expectedCity: '',
  expectedJob: '',
  expectedSalary: ''
})

const rules = {
  expectedCity: [{ required: true, message: '请选择期望城市', trigger: 'change' }],
  expectedJob: [{ required: true, message: '请输入期望职位', trigger: 'blur' }],
  expectedSalary: [{ required: true, message: '请选择期望薪资', trigger: 'change' }]
}

// 热门职位词(与找职位页同源), 点选即填入输入框, 仍可手动修改
const hotKeywords = computed(() => jobStore.hots || [])
const selectHot = (kw) => {
  form.expectedJob = kw
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    const updated = await request.post('/user/onboarding', {
      expected_city: form.expectedCity,
      expected_job: form.expectedJob,
      expected_salary: form.expectedSalary
    })
    // 合并最新用户信息(含 onboarded=true), 同步 localStorage
    userStore.userInfo = { ...(userStore.userInfo || {}), ...updated }
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    ElMessage.success('建档完成, 为你打开匹配的岗位')
    // 首跳: 三项筛选自动带入找职位页
    router.push({
      path: '/jobs',
      query: {
        keyword: form.expectedJob,
        city: form.expectedCity,
        salaryRange: form.expectedSalary
      }
    })
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

// 退出登录: 登错号时的换号出口(二次确认, 防止误点丢表单)
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '退出后当前填写的期望不会保存, 确定退出登录?',
      '退出登录',
      { confirmButtonText: '退出', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

onMounted(() => {
  // 热门词加载失败不阻塞建档
  jobStore.getHots().catch(() => {})
})
</script>

<style scoped>
.onboarding-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.logout-btn {
  position: absolute;
  top: 20px;
  right: 24px;
  z-index: 2;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
}

/* 覆盖 Element 文字按钮默认的浅色 hover 底(白底白字看不见), 改成半透明白底+纯白字 */
.onboarding-page .el-button.logout-btn:hover,
.onboarding-page .el-button.logout-btn:focus,
.onboarding-page .el-button.logout-btn:focus-visible {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.18);
}

.onboarding-page .el-button.logout-btn:active {
  background-color: rgba(255, 255, 255, 0.28);
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

.onboarding-card {
  width: 460px;
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  z-index: 1;
}

.onboarding-header {
  text-align: center;
  margin-bottom: 28px;
}

.onboarding-header h1 {
  font-size: 24px;
  color: #303133;
  margin: 12px 0 6px;
}

.onboarding-header p {
  color: #909399;
  font-size: 13px;
}

.hot-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.hot-tags-label {
  color: #909399;
  font-size: 12px;
}

.onboarding-submit {
  width: 100%;
  margin-top: 4px;
}

.onboarding-tip {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 12px;
}
</style>
