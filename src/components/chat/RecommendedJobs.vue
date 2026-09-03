<template>
  <div class="rj-wrap">
    <div class="rj-title">🎯 顾问为你匹配的岗位 <span class="rj-hint">点击卡片可查看岗位详情</span></div>
    <div class="rj-grid">
      <div
        v-for="(job, i) in jobs"
        :key="job.job_id ?? i"
        class="rj-card"
        @click="openJob(job)"
      >
        <div class="rj-head">
          <div class="rj-title-row">
            <span class="rj-name">{{ job.title }}</span>
            <span v-if="job.match_score != null" class="rj-score" :class="scoreCls(job.match_score)">
              {{ job.match_score }}<em>%</em>
            </span>
          </div>
          <div class="rj-company">{{ job.company }}</div>
        </div>
        <div class="rj-tags">
          <span v-if="job.city" class="rj-tag">📍{{ job.city }}</span>
          <span v-if="job.salary" class="rj-tag rj-salary">💰{{ job.salary }}</span>
          <span v-if="job.experience" class="rj-tag">{{ job.experience }}</span>
          <span v-if="job.education" class="rj-tag">{{ job.education }}</span>
        </div>
        <div v-if="job.match_reason" class="rj-reason">{{ job.match_reason }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  jobs: { type: Array, default: () => [] },
})

const router = useRouter()

function scoreCls(score) {
  if (score >= 85) return 'high'
  if (score >= 70) return 'mid'
  return 'low'
}

function openJob(job) {
  if (job.job_id) {
    // ?from=consultant 标记从 AI 顾问卡片进来的 → 岗位详情页显示"返回 AI 顾问",
    // 回去后顾问会话原样保留(useChat 状态是模块级单例, 不会因组件卸载丢失)
    router.push({ path: '/jobs/' + job.job_id, query: { from: 'consultant' } })
  }
}
</script>

<style scoped>
.rj-wrap {
  margin-top: 10px;
  max-width: 70%;
}

.rj-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}
.rj-hint {
  font-weight: 400;
  font-size: 11px;
  color: #999;
  margin-left: 6px;
}

.rj-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.rj-card {
  background: #f7f8fd;
  border: 1px solid #e8eaf6;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.1s;
}
.rj-card:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.18);
  transform: translateY(-1px);
}

.rj-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.rj-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rj-score {
  flex-shrink: 0;
  font-size: 15px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 10px;
  color: #fff;
}
.rj-score em {
  font-style: normal;
  font-size: 11px;
  font-weight: 400;
}
.rj-score.high { background: #34c77b; }
.rj-score.mid  { background: #f0a63b; }
.rj-score.low  { background: #ee6d66; }

.rj-company {
  font-size: 12px;
  color: #667eea;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rj-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 7px;
}
.rj-tag {
  font-size: 11px;
  color: #606266;
  background: #fff;
  border-radius: 6px;
  padding: 1px 6px;
  border: 1px solid #e5e7f0;
}
.rj-salary {
  color: #ff5722;
  border-color: #ffd8cc;
}

.rj-reason {
  margin-top: 7px;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 768px) {
  .rj-wrap { max-width: 85%; }
  .rj-grid { grid-template-columns: 1fr; }
}
</style>
