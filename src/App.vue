<template>
  <router-view />
</template>

<script setup>
// 根组件,直接通过 router-view 渲染对应页面
// 全局布局在 layouts/MainLayout.vue 中处理
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 刷新页面时:如果已登录,从后端拉一次最新用户信息
onMounted(async () => {
  if (!userStore.isLoggedIn) return
  try {
    await userStore.fetchUserInfo()
  } catch {
    userStore.logout()
  }
})
</script>

<style>
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}
</style>
