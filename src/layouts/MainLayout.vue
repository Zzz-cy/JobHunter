<template>
  <el-container class="layout-container">
    <!-- 顶部导航 -->
    <el-header class="layout-header">
      <AppHeader />
    </el-header>

    <!-- 主内容区 -->
    <el-main class="layout-main">
      <router-view v-slot="{ Component, route }">
        <transition name="fade" mode="out-in">
          <!-- keep-alive:缓存列表页等"状态重要"的页面,
               从详情页返回时保留筛选条件/分页/滚动位置,不重新请求 -->
          <keep-alive :include="['JobList']">
            <component :is="Component" :key="route.fullPath" />
          </keep-alive>
        </transition>
      </router-view>
    </el-main>

    <!-- 底部 -->
    <el-footer class="layout-footer">
      <AppFooter />
    </el-footer>
  </el-container>
</template>

<script setup>
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.layout-header {
  height: 64px;
  padding: 0;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.layout-main {
  flex: 1;
  padding: 0;
  background: #f5f7fa;
}

.layout-footer {
  height: auto;
  padding: 0;
  background: #2c3e50;
  color: #c0c4cc;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
