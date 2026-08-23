<template>
  <div class="not-found-page">
    <div class="nf-content">
      <div class="nf-code">404</div>
      <h2 class="nf-title">页面走丢了</h2>
      <p class="nf-desc">你访问的页面不存在,可能已被移除或链接错误</p>
      <div class="nf-actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-button @click="goJobs">去看看职位</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const goHome = () => router.push('/home')
const goJobs = () => router.push('/jobs')
</script>

<style scoped>
.not-found-page {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nf-content {
  text-align: center;
  padding: 40px;
}

.nf-code {
  font-size: 120px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1;
}

.nf-title {
  font-size: 24px;
  color: #303133;
  margin: 16px 0 8px;
}

.nf-desc {
  color: #909399;
  margin-bottom: 24px;
}

.nf-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
