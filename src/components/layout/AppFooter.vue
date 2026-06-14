<template>
  <div class="app-footer">
    <div class="footer-inner">
      <div class="footer-left">
        <div class="footer-logo">
          <el-icon :size="20" color="#409eff"><Promotion /></el-icon>
          <span>JobHunter</span>
        </div>
        <p class="footer-desc">智能求职推荐平台 · 数据聚合 + 知识图谱 + AI 推荐</p>
      </div>

      <div class="footer-right">
        <div class="footer-links">
          <span class="link-title">数据来源</span>
          <a href="https://www.zhipin.com" target="_blank" rel="noopener">Boss直聘</a>
          <a href="https://www.liepin.com" target="_blank" rel="noopener">猎聘</a>
          <a href="https://www.lagou.com" target="_blank" rel="noopener">拉勾网</a>
        </div>
        <div class="footer-links">
          <span class="link-title">友情提示</span>
          <span class="footer-tip">本站仅提供招聘信息聚合,投递请前往原网站</span>
        </div>
      </div>
    </div>
    <div class="footer-copyright">
      © 2026 JobHunter · 仅供学习研究使用
    </div>
  </div>
</template>

<script setup>
// 静态底部,无逻辑
</script>

<style scoped>
.app-footer {
  padding: 32px 24px 16px;
}

.footer-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  gap: 48px;
}

.footer-left {
  flex: 0 0 320px;
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 12px;
}

.footer-desc {
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.footer-right {
  display: flex;
  gap: 80px;
}

.footer-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.link-title {
  color: #c0c4cc;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.footer-links a {
  color: #909399;
  font-size: 13px;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: #409eff;
}

.footer-tip {
  color: #909399;
  font-size: 12px;
  max-width: 280px;
  line-height: 1.6;
}

.footer-copyright {
  max-width: 1400px;
  margin: 24px auto 0;
  padding-top: 16px;
  border-top: 1px solid #3a4a5c;
  text-align: center;
  color: #606266;
  font-size: 12px;
}
</style>
