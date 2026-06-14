<template>
  <el-card class="job-card hover-card" shadow="hover" @click="handleClick">
    <div class="card-header">
      <div class="job-title">{{ job.title || '职位名称' }}</div>
      <div class="job-salary">{{ salaryText }}</div>
    </div>

    <div class="card-meta">
      <span class="meta-item">
        <el-icon><Location /></el-icon>
        {{ job.city || '城市未知' }}
      </span>
      <span class="meta-item">
        <el-icon><Briefcase /></el-icon>
        {{ job.experience_req || '经验不限' }}
      </span>
      <span class="meta-item">
        <el-icon><Reading /></el-icon>
        {{ job.education_req || '学历不限' }}
      </span>
      <span class="meta-item" v-if="job.job_type">
        <el-icon><Clock /></el-icon>
        {{ jobTypeText }}
      </span>
    </div>

    <div class="card-tags" v-if="job.highlights && job.highlights.length">
      <el-tag
        v-for="tag in job.highlights.slice(0, 4)"
        :key="tag"
        size="small"
        type="info"
        effect="plain"
      >
        {{ tag }}
      </el-tag>
    </div>

    <div class="card-footer">
      <div class="company-info">
        <el-avatar :size="28" :src="job.company_logo">
          {{ (job.company_name || '?').charAt(0) }}
        </el-avatar>
        <div class="company-detail">
          <div class="company-name">{{ job.company_name || '公司名称' }}</div>
          <div class="company-meta">
            {{ job.industry || '行业未知' }} · {{ job.size || '规模未知' }}
          </div>
        </div>
      </div>
      <el-tag size="small" :type="sourceTagType">{{ sourceText }}</el-tag>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  job: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['click'])

const salaryText = computed(() => {
  const j = props.job
  if (!j.salary_min && !j.salary_max) return '薪资面议'
  const unit = j.salary_unit === 'day' ? '元/天' : j.salary_unit === 'year' ? 'K/年' : 'K'
  if (j.salary_min && j.salary_max) {
    return `${j.salary_min}-${j.salary_max}${unit}${j.salary_months ? `·${j.salary_months}薪` : ''}`
  }
  return `${j.salary_min || j.salary_max}${unit}`
})

const jobTypeText = computed(() => {
  const map = { full: '全职', part: '兼职', intern: '实习' }
  return map[props.job.job_type] || props.job.job_type
})

const sourceText = computed(() => {
  const map = { boss: 'Boss直聘', liepin: '猎聘', official: '官方' }
  return map[props.job.source] || props.job.source || ''
})

const sourceTagType = computed(() => {
  const map = { boss: 'success', liepin: 'warning', official: 'info' }
  return map[props.job.source] || 'info'
})

const handleClick = () => emit('click', props.job)
</script>

<style scoped>
.job-card {
  cursor: pointer;
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.job-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  flex: 1;
  margin-right: 12px;
}

.job-salary {
  font-size: 16px;
  font-weight: 600;
  color: #ff5722;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.company-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.company-name {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.company-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
</style>
