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
            <el-tab-pane label="点击过" name="clicked" />
            <el-tab-pane label="已收藏" name="favorited" />
            <el-tab-pane label="已投递" name="submitted" />
            <el-tab-pane label="面试中" name="interviewed" />
            <el-tab-pane label="Offer" name="offer" />
            <el-tab-pane label="未通过" name="rejected" />
          </el-tabs>

          <el-empty v-if="!applications.length" description="暂无求职进度记录" />

          <div v-else class="app-list">
            <div v-for="app in applications" :key="app.id" class="app-item">
              <div class="app-main" @click="goJobDetail(app)">
                <div class="app-title">{{ app.job_title || app.job?.title }}</div>
                <div class="app-meta">
                  {{ app.company_name || app.job?.company_name }}
                  · {{ app.job?.city }}
                  · {{ app.job?.salary_text }}
                </div>
                <div class="app-time">
                  跳转时间: {{ formatTime(app.redirected_at) }}
                  <span v-if="app.submitted_at">
                    · 投递: {{ formatTime(app.submitted_at) }}
                  </span>
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
                  <el-option label="点击过" value="clicked" />
                  <el-option label="已收藏" value="favorited" />
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

          <div v-else>
            <JobCard
              v-for="job in favoriteJobs"
              :key="job.id"
              :job="job"
              @click="goJobDetail(job)"
            />
          </div>
        </el-card>

        <!-- 账号设置 -->
        <el-card v-if="activeTab === 'settings'" class="content-card" shadow="never">
          <template #header>
            <div class="card-title">账号设置</div>
          </template>

          <el-form
            :model="settings"
            label-width="100px"
            style="max-width: 500px"
          >
            <el-form-item label="昵称">
              <el-input v-model="settings.nickname" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="settings.email" placeholder="选填" />
            </el-form-item>
            <el-form-item label="求职意向">
              <el-input
                v-model="settings.intent"
                type="textarea"
                :rows="3"
                placeholder="例如:Python 后端,北京,期望 25-35K"
              />
            </el-form-item>
            <el-form-item label="期望城市">
              <el-select v-model="settings.expectCity" placeholder="选择期望城市" clearable>
                <el-option v-for="c in cityOptions" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="期望薪资">
              <el-slider
                v-model="settings.expectSalary"
                range
                :min="0"
                :max="100"
                :step="5"
                :marks="{ 0: '0K', 50: '50K', 100: '100K+' }"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSettings">保存</el-button>
              <el-button @click="resetSettings">重置</el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="danger-zone">
            <h4>危险操作</h4>
            <el-button type="danger" plain @click="changePassword">修改密码</el-button>
            <el-button type="danger" plain @click="logoutAll">退出所有设备</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import JobCard from '@/components/common/JobCard.vue'
// import { useUserStore } from '@/stores/user'
// import request from '@/utils/request'

const router = useRouter()
// const userStore = useUserStore()

const activeTab = ref('jobs')
const jobStatus = ref('clicked')
const applications = ref([])
const favoriteJobs = ref([])

const userInfo = computed(() => ({
  nickname: '',
  phone: '',
  avatar_url: ''
}))
const username = computed(() => userInfo.value.nickname || '')

const settings = reactive({
  nickname: '',
  email: '',
  intent: '',
  expectCity: '',
  expectSalary: [10, 30]
})

const cityOptions = ['北京', '上海', '深圳', '广州', '杭州', '成都', '南京', '武汉', '西安']

const handleStatusChange = () => {
  loadApplications()
}

const loadApplications = async () => {
  // TODO: 拉取求职进度列表
  // const res = await request.get('/applications', {
  //   params: { status: jobStatus.value, page: 1, pageSize: 50 }
  // })
  // applications.value = res.list
  console.log('[TODO] loadApplications', jobStatus.value)
}

const loadFavorites = async () => {
  // TODO: 拉取收藏列表
  // const res = await request.get('/applications/favorites')
  // favoriteJobs.value = res.list
  console.log('[TODO] loadFavorites')
}

const updateStatus = async (app) => {
  // TODO: 更新 application 状态
  // await request.put(`/applications/${app.id}`, {
  //   status: app.status,
  //   feedback_at: new Date()
  // })
  ElMessage.success('状态已更新')
}

const editNote = async (app) => {
  try {
    const { value } = await ElMessageBox.prompt('编辑备注', '面试进度/HR 联系等', {
      inputValue: app.note || '',
      inputType: 'textarea'
    })
    // TODO: 保存备注
    // await request.put(`/applications/${app.id}`, { note: value })
    app.note = value
    ElMessage.success('备注已保存')
  } catch {}
}

const goApply = (app) => {
  const url = app.source_url || app.job?.source_url
  if (!url) {
    ElMessage.warning('未找到原站链接')
    return
  }
  window.open(url, '_blank', 'noopener')
}

const goJobDetail = (app) => {
  const jobId = app.job_id || app.job?.id
  if (jobId) router.push(`/jobs/${jobId}`)
}

const saveSettings = async () => {
  // TODO: 调用后端保存设置
  // await request.put('/user/settings', settings)
  ElMessage.success('设置已保存')
}

const resetSettings = () => {
  Object.assign(settings, {
    nickname: '',
    email: '',
    intent: '',
    expectCity: '',
    expectSalary: [10, 30]
  })
}

const changePassword = () => {
  ElNotification.info('修改密码功能待实现')
}

const logoutAll = async () => {
  try {
    await ElMessageBox.confirm('确定要退出所有设备的登录状态吗?', '提示', {
      type: 'warning'
    })
    // TODO: 调用退出所有设备接口
    ElMessage.success('已退出所有设备')
    router.push('/login')
  } catch {}
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

// TODO: 初始化加载
// import { onMounted } from 'vue'
// onMounted(() => {
//   loadApplications()
//   loadFavorites()
// })
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

.danger-zone h4 {
  color: #f56c6c;
  margin-bottom: 12px;
}
</style>
