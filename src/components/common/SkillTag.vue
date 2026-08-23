<template>
  <el-tag
    :type="tagType"
    :size="size"
    :effect="effect"
    class="skill-tag"
    @click="$emit('click', skill)"
  >
    <el-icon v-if="skill.is_hot" color="#f56c6c"><Star /></el-icon>
    {{ displayName }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  skill: {
    type: Object,
    default: () => ({})
  },
  size: {
    type: String,
    default: 'default'
  },
  effect: {
    type: String,
    default: 'light'
  }
})

defineEmits(['click'])

// 兼容两种字段名:
//   - 简历技能(SkillOut): 字段叫 name
//   - 职位技能(JobSkillOut): 字段叫 skill_name
// 取不到时回退显示 skill_id, 避免完全空白
const displayName = computed(() => {
  return props.skill.skill_name || props.skill.name || `技能#${props.skill.skill_id || props.skill.id || ''}`
})

const tagType = computed(() => {
  const map = { 语言: 'primary', 框架: 'success', 工具: 'warning', 方向: 'info', 软技能: '' }
  return map[props.skill.category] || ''
})
</script>

<style scoped>
.skill-tag {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
