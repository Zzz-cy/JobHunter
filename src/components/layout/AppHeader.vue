<template>
  <div class="app-header">
    <div class="header-inner">
      <!-- Logo -->
      <div class="logo" @click="goHome">
        <el-icon :size="28" color="#409eff"><Promotion /></el-icon>
        <span class="logo-text">JobHunter</span>
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        mode="horizontal"
        :ellipsis="false"
        router
        class="nav-menu"
      >
        <el-menu-item index="/home">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/jobs">
          <el-icon><Search /></el-icon>
          <span>找职位</span>
        </el-menu-item>
        <el-menu-item index="/recommend">
          <el-icon><MagicStick /></el-icon>
          <span>智能推荐</span>
        </el-menu-item>
        <el-menu-item index="/resume">
          <el-icon><Document /></el-icon>
          <span>我的简历</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据分析</span>
        </el-menu-item>
      </el-menu>

      <!-- 用户操作区 -->
      <div class="user-area">
        <template v-if="isLoggedIn">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :src="userInfo?.avatar_url">
                {{ username.charAt(0).toUpperCase() }}
              </el-avatar>
              <span class="username">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人中心
                </el-dropdown-item>
                <el-dropdown-item command="resume">
                  <el-icon><Document /></el-icon> 我的简历
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button type="text" @click="goLogin">登录</el-button>
          <el-button type="primary" @click="goRegister">注册</el-button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// import { useUserStore } from '@/stores/user'
// import { ElMessageBox, ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
// const userStore = useUserStore()

// 登录态(占位,等接入 store 后改)
const isLoggedIn = computed(() => false)
const userInfo = computed(() => null)
const username = computed(() => '')

// 高亮当前菜单
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/jobs')) return '/jobs'
  if (path.startsWith('/resume')) return '/resume'
  return path
})

const goHome = () => router.push('/home')
const goLogin = () => router.push('/login')
const goRegister = () => router.push('/register')

const handleCommand = async (cmd) => {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'resume') {
    router.push('/resume')
  } else if (cmd === 'logout') {
    // TODO: 接入 user store 后实现退出
    // await ElMessageBox.confirm('确定要退出登录吗?', '提示', { type: 'warning' })
    // await userStore.logout()
    // ElMessage.success('已退出登录')
    // router.push('/home')
  }
}
</script>

<style scoped>
.app-header {
  height: 64px;
}

.header-inner {
  max-width: 1400px;
  height: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  margin-right: 48px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
}

.nav-menu {
  flex: 1;
  border-bottom: none !important;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.username {
  font-size: 14px;
  color: #606266;
}
</style>
