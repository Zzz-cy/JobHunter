<template>
  <div class="app-header">
    <div class="header-inner">
      <!-- Logo -->
      <div class="logo" @click="goHome">
        <el-icon :size="28" color="#409eff"><Promotion /></el-icon>
        <span class="logo-text">JobHunter</span>
      </div>

      <!-- 导航菜单 -->
      <!-- 不关 ellipsis: 菜单项过多时自动折叠进「···」, 防止挤压右侧用户区 -->
      <el-menu
        :default-active="activeMenu"
        mode="horizontal"
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
        <el-menu-item index="/job-recommend">
          <el-icon><Aim /></el-icon>
          <span>岗位推荐</span>
        </el-menu-item>
        <el-menu-item index="/resume">
          <el-icon><Document /></el-icon>
          <span>我的简历</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据分析</span>
        </el-menu-item>
        <el-menu-item index="/job-definitions">
          <el-icon><Compass /></el-icon>
          <span>岗位发现</span>
        </el-menu-item>
        <el-menu-item index="/recommend">
          <el-icon><MagicStick /></el-icon>
          <span>AI 求职顾问</span>
        </el-menu-item>
        <el-menu-item index="/knowledge-graph">
          <el-icon><Connection /></el-icon>
          <span>知识图谱</span>
        </el-menu-item>
        <el-menu-item index="/data-admin" v-if="isAdmin">
          <el-icon><DataLine /></el-icon>
          <span>数据管理</span>
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
          <el-button link type="primary" @click="goLogin">登录</el-button>
          <el-button type="primary" @click="goRegister">注册</el-button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { ElMessageBox, ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 登录态
const { isLoggedIn, userInfo, username, isAdmin } = storeToRefs(userStore)

// 高亮当前菜单
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/jobs')) return '/jobs'
  if (path.startsWith('/resume')) return '/resume'
  if (path.startsWith('/data-admin')) return '/data-admin'
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
    await ElMessageBox.confirm('确定要退出登录吗?', '提示', { type: 'warning' })
    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/home')
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
  margin-right: 24px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
  white-space: nowrap;
}

.nav-menu {
  flex: 1;
  min-width: 0;   /* 允许收缩, ellipsis 折叠才会触发 */
  border-bottom: none !important;
}

/* 菜单项多, 左右边距收窄一点 */
.nav-menu :deep(.el-menu-item) {
  padding: 0 14px;
}

.nav-menu :deep(.el-menu-item .el-icon) {
  margin-right: 2px;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;   /* 不被菜单挤压, 否则头像会变形 */
  margin-left: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
  flex-shrink: 0;
}

/* 头像固定方形, 不参与 flex 收缩 */
.user-info :deep(.el-avatar) {
  flex-shrink: 0;
}

.username {
  font-size: 14px;
  color: #606266;
}
</style>
