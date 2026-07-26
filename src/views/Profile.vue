<template>
  <div class="profile-page page-container">
    <el-row :gutter="20">
      <!-- 左侧:用户卡片 -->
      <el-col :span="6">
        <el-card class="user-card" shadow="never">
          <div class="user-info">
            <el-avatar :size="80" :src="userInfo.avatar_url">
              {{ username.charAt(0).toUpperCase() }}
            </el-avatar>
            <h3 class="user-name">{{ userInfo.nickname || '用户' }}</h3>
            <p class="user-phone">{{ userInfo.phone || '' }}</p>
          </div>

          <el-menu :default-active="activeTab" @select="activeTab = $event">
            <el-menu-item index="jobs">
              <el-icon><Briefcase /></el-icon>
              <span>我的求职进度</span>
            </el-menu-item>
            <el-menu-item index="favorites">
              <el-icon><Star /></el-icon>
              <span>我的收藏</span>
            </el-menu-item>
            <el-menu-item index="settings">
              <el-icon><Setting /></el-icon>
              <span>账号设置</span>
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>

      <!-- 右侧:内容区 -->
      <el-col :span="18">
        <!-- 求职进度 -->
        <el-card v-if="activeTab === 'jobs'" class="content-card" shadow="never">
          <template #header>
            <div class="card-title">
              <span>我的求职进度</span>
              <el-tooltip content="求职进度需要你手动反馈,本站不代投" placement="top">
                <el-icon color="#909399"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>

          <el-tabs v-model="jobStatus" @tab-change="handleStatusChange">
            <el-tab-pane label="已投递" name="submitted" />
            <el-tab-pane label="面试中" name="interviewed" />
            <el-tab-pane label="Offer" name="offer" />
            <el-tab-pane label="未通过" name="rejected" />
          </el-tabs>

          <el-empty v-if="!filteredApplications.length" description="该状态下暂无记录" />

          <div v-else class="app-list">
            <div v-for="app in filteredApplications" :key="app.id" class="app-item">
              <div class="app-main" @click="goJobDetail(app)">
                <div class="app-title">{{ app.job?.title }}</div>
                <div class="app-meta">
                  {{ app.job?.company.name}}
                  · {{ app.job?.city }}
                  · {{ formatSalary(app.job) }}
                </div>
                <div class="app-time" v-if="app.submitted_at">
                  投递时间: {{ formatTime(app.submitted_at) }}
                </div>
                <div class="app-note" v-if="app.note">
                  <el-icon><EditPen /></el-icon>
                  {{ app.note }}
                </div>
              </div>
              <div class="app-actions">
                <el-select
                  v-model="app.status"
                  size="small"
                  style="width: 110px"
                  @change="updateStatus(app)"
                >
                  <el-option label="已投递" value="submitted" />
                  <el-option label="面试中" value="interviewed" />
                  <el-option label="Offer" value="offer" />
                  <el-option label="未通过" value="rejected" />
                </el-select>
                <el-button size="small" text @click="editNote(app)">
                  <el-icon><EditPen /></el-icon>
                </el-button>
                <el-button size="small" text @click="goApply(app)">
                  <el-icon><Link /></el-icon>
                </el-button>
                <el-button size="small" text type="danger" @click="deleteApplication(app)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 我的收藏 -->
        <el-card v-if="activeTab === 'favorites'" class="content-card" shadow="never">
          <template #header>
            <div class="card-title">
              <span>我的收藏 ({{ favoriteJobs.length }})</span>
            </div>
          </template>

          <el-empty v-if="!favoriteJobs.length" description="还没有收藏的职位" />

          <div v-else class="favorite-list">
            <div v-for="job in favoriteJobs" :key="job.id" class="favorite-item">
              <JobCard :job="job" @click="goJobDetail(job)" />
              <div class="favorite-actions">
                <el-button size="small" type="danger" plain @click="unfavorite(job)">
                  <el-icon><StarFilled /></el-icon>
                  取消收藏
                </el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 账号设置 -->
        <el-card v-if="activeTab === 'settings'" class="content-card" shadow="never">
          <template #header>
            <div class="card-title">账号设置</div>
          </template>

          <el-form
            ref="settingsFormRef"
            :model="settings"
            :rules="settingsRules"
            label-width="100px"
            style="max-width: 500px"
          >
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="settings.nickname" placeholder="未设置" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input
                v-model="settings.phone"
                placeholder="未设置"
                maxlength="11"
              />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="settings.email" placeholder="未设置" />
            </el-form-item>
            <el-form-item label="原密码" prop="oldPassword">
              <el-input
                v-model="settings.oldPassword"
                type="password"
                placeholder="不修改请留空"
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="settings.newPassword"
                type="password"
                placeholder="不修改请留空"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input
                v-model="settings.confirmPassword"
                type="password"
                placeholder="再次输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSettings">保存</el-button>
              <el-button @click="resetSettings">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import JobCard from '@/components/common/JobCard.vue'
import { useUserStore } from '@/stores/user'
import { useJobStore } from '@/stores/job'
import request from '@/utils/request'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const jobStore = useJobStore()

const validTabs = ['jobs', 'favorites', 'settings']
const activeTab = ref(validTabs.includes(route.query.tab) ? route.query.tab : 'jobs')
const jobStatus = ref('submitted')
const applications = ref([])         // 全部投递记录(从后端拉一次)
const favoriteJobs = ref([])

// 按当前 tab(submitted/interviewed/offer/rejected)过滤投递记录
// 切 tab 时不用重新请求,这个 computed 自动重算
const filteredApplications = computed(() => {
  return applications.value.filter(a => a.status === jobStatus.value)
})

// 用户信息直接从 store 读(登录后/改资料后都会同步更新)
const userInfo = computed(() => userStore.userInfo || {})
const username = computed(() => userInfo.value.nickname || userInfo.value.phone || '用户')

const settings = reactive({
  nickname: '',
  phone: '',
  email: '',
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const handleStatusChange = () => {
  // 切 tab 不用重新拉接口,本地 computed 过滤即可(数据量小,体验更快)
}

const loadApplications = async () => {
  // 拉全部投递记录(不过滤 status),本地用 computed 按 tab 过滤
  const res = await request.get('/user/applications')
  applications.value = res
}

const loadFavorites = async () => {
  favoriteJobs.value = await request.get('/user/applications/favorites')
}

// 删除求职进度记录
const deleteApplication = async (app) => {
  try {
    await ElMessageBox.confirm('确定要删除这条求职进度吗?', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    const jobId = app.job?.id || app.job_id
    await request.delete(`/user/delete_application/${jobId}`)
    // 从本地列表移除(不用重新拉接口,体验更快)
    applications.value = applications.value.filter(a => (a.job?.id || a.job_id) !== jobId)
    // ★ 同步更新 store 的 appliedIds
    jobStore.appliedIds.delete(Number(jobId))
    ElMessage.success('已删除')
  } catch (err) {
    if (err !== 'cancel' && err?.message) ElMessage.error(err.message)
  }
}

// 取消收藏(用户在我的收藏页点取消收藏按钮)
const unfavorite = async (job) => {
  try {
    await ElMessageBox.confirm(`确定取消收藏「${job.title}」吗?`, '提示', {
      type: 'warning',
      confirmButtonText: '取消收藏',
      cancelButtonText: '保留'
    })
    await request.delete(`/jobs/applications/${job.id}/favorite`)
    // 从本地列表移除
    favoriteJobs.value = favoriteJobs.value.filter(j => j.id !== job.id)
    // ★ 同步更新 store 的 favoriteIds
    jobStore.favoriteIds.delete(Number(job.id))
    ElMessage.success('已取消收藏')
  } catch (err) {
    if (err !== 'cancel' && err?.message) ElMessage.error(err.message)
  }
}

const updateStatus = async (app) => {
  try {
    const jobId = app.job?.id || app.job_id
    await request.put('/user/update_application', {
      job_id: jobId,
      status: app.status
    })
    ElMessage.success('状态已更新')
  } catch (err) {
    if (err?.message) ElMessage.error(err.message)
  }
}

const editNote = async (app) => {
  try {
    const { value } = await ElMessageBox.prompt('编辑备注', '面试进度/HR 联系等', {
      inputValue: app.note || '',
      inputType: 'textarea'
    })
    // 调"修改求职进度"接口(跟 updateStatus 共用,同时支持 status/note)
    const jobId = app.job?.id || app.job_id
    await request.put('/user/update_application', {
      job_id: jobId,
      note: value
    })
    // 同步本地状态
    app.note = value
    ElMessage.success('备注已保存')
  } catch (err) {
    // 用户点取消会 reject,不算错误
    if (err !== 'cancel' && err?.message) ElMessage.error(err.message)
  }
}

const goApply = (app) => {
  const url = app.job?.source_url
  if (!url) {
    ElMessage.warning('未找到原站链接')
    return
  }
  window.open(url, '_blank', 'noopener')
}

const goJobDetail = (app) => {
  const jobId = app.job?.id
  if (jobId) router.push(`/jobs/${jobId}`)
}

const settingsFormRef = ref(null)

// 保存设置:统一表单提交
const saveSettings = async () => {
  if (!settingsFormRef.value) return
  try {
    await settingsFormRef.value.validate()

    // 改密码时,原密码和新密码必须同时填或同时不填
    const hasOld = !!settings.oldPassword
    const hasNew = !!settings.newPassword
    if (hasOld !== hasNew) {
      ElMessage.warning('请把原密码和新密码都填上,或都留空')
      return
    }

    // 构造请求体:只传非空字段,避免把空字符串当新值传给后端
    // 后端 PUT /user/update 是综合接口,资料和密码一次搞定
    const payload = {}
    if (settings.nickname) payload.nickname = settings.nickname
    if (settings.phone) payload.phone = settings.phone
    if (settings.email) payload.email = settings.email
    if (hasOld && hasNew) {
      payload.old_password = settings.oldPassword
      payload.new_password = settings.newPassword
    }

    if (Object.keys(payload).length === 0) {
      ElMessage.info('没有要保存的改动')
      return
    }

    await request.put('/user/update', payload)

    // 保存成功后,同步刷新 store 里的 userInfo(右上角头像旁的昵称等会跟着更新)
    await userStore.fetchUserInfo()

    // 提示:改了密码就提示密码,否则提示资料
    ElMessage.success(hasOld && hasNew ? '密码已修改' : '设置已保存')

    // 清空密码框(昵称/手机号/邮箱保留显示)
    settings.oldPassword = ''
    settings.newPassword = ''
    settings.confirmPassword = ''
  } catch (err) {
    // 校验失败 Element Plus 自动在表单上提示错误
    if (err?.message) ElMessage.error(err.message)
  }
}

const resetSettings = () => {
  Object.assign(settings, {
    nickname: '',
    phone: '',
    email: '',
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
}

// 确认密码校验:必须和新密码一致
const validateConfirm = (_rule, value, callback) => {
  if (value !== settings.newPassword) callback(new Error('两次输入的密码不一致'))
  else callback()
}

// 账号设置表单的校验规则
const settingsRules = {
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  newPassword: [
    { min: 6, max: 20, message: '密码 6-20 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { validator: validateConfirm, trigger: 'blur' }
  ]
}


const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

// 把薪资 min/max(单位 K)拼成展示文本
const formatSalary = (job) => {
  if (!job) return ''
  const min = job.salary_min
  const max = job.salary_max
  if (min == null && max == null) return '薪资面议'
  if (min != null && max != null) return `${min}-${max}K`
  return `${min ?? max}K`
}

import { onMounted } from 'vue'

const loadUserInfo = async () => {
  try {
    const info = userStore.userInfo || {}
    Object.assign(settings, {
      nickname: info.nickname || '',
      phone: info.phone || '',
      email: info.email || ''
    })

    // 如果 store 里没数据(比如刷新后 localStorage 被清),再调后端拉一次
    if (!info.id) {
      await userStore.fetchUserInfo()
      const fresh = userStore.userInfo || {}
      Object.assign(settings, {
        nickname: fresh.nickname || '',
        phone: fresh.phone || '',
        email: fresh.email || ''
      })
    }
  } catch (err) {
    console.error('加载用户信息失败', err)
  }
}

onMounted(() => {
  loadUserInfo()
  loadApplications()
  loadFavorites()
})
</script>

<style scoped>
.user-card {
  margin-bottom: 16px;
}

.user-info {
  text-align: center;
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 12px;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 12px 0 4px;
}

.user-phone {
  color: #909399;
  font-size: 12px;
}

.content-card {
  min-height: 600px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #303133;
}

.app-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.app-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  transition: all 0.2s;
}

.app-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.app-main {
  flex: 1;
  cursor: pointer;
  min-width: 0;
}

.app-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.app-main:hover .app-title {
  color: #409eff;
}

.app-meta {
  color: #606266;
  font-size: 13px;
  margin-bottom: 4px;
}

.app-time {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}

.app-note {
  color: #606266;
  font-size: 12px;
  background: #f5f7fa;
  padding: 6px 10px;
  border-radius: 4px;
  display: flex;
  gap: 4px;
  align-items: flex-start;
}

.app-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 我的收藏列表:每个卡片下面带一个取消收藏按钮 */
.favorite-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.favorite-item {
  position: relative;
}
.favorite-actions {
  margin-top: 8px;
  text-align: right;
}

.danger-zone h4 {
  color: #f56c6c;
  margin-bottom: 12px;
}
</style>
