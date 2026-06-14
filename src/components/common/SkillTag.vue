<template>
  <el-tag
    :type="tagType"
    :size="size"
    :effect="effect"
    class="skill-tag"
    @click="$emit('click', skill)"
  >
    <el-icon v-if="skill.is_hot" color="#f56c6c"><Star /></el-icon>
    {{ skill.name }}
    <span v-if="skill.proficiency" class="skill-level">L{{ skill.proficiency }}</span>
    <span v-if="skill.years" class="skill-years">{{ skill.years }}年</span>
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

.skill-level {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.7;
}

.skill-years {
  margin-left: 2px;
  font-size: 11px;
  opacity: 0.7;
}
</style>
