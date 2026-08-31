<template>
  <div class="page-container kg-page">
    <!-- 页头:标题 + 方向选择器 -->
    <div class="page-header kg-header">
      <div>
        <h1 class="page-title">岗位知识图谱</h1>
        <p class="page-desc">基于 Neo4j 的岗位方向画像:热门城市 / 学历 / 经验 / 薪资 / 福利 / 相似方向</p>
      </div>
      <el-select
        v-model="keyword"
        :loading="dirLoading"
        placeholder="选择岗位方向"
        filterable
        class="kg-select"
        @change="fetchGraphData"
      >
        <el-option
          v-for="d in directions"
          :key="d.name"
          :value="d.name"
          :label="`${d.name}(${d.total_jobs || 0} 个岗位)`"
        />
      </el-select>
    </div>

    <!-- 图谱卡片 -->
    <el-card shadow="never" class="kg-card">
      <div class="kg-wrapper" v-loading="loading" element-loading-text="图谱加载中…">
        <!-- 状态栏 -->
        <div class="kg-toolbar">
          <span class="kg-tag" v-if="fromMock">⚠ 演示数据(后端不可用)</span>
          <span class="kg-tag ok" v-else>✓ Neo4j 实时数据</span>
          <span class="kg-meta">{{ graphNodes.length }} 节点 · {{ graphLinks.length }} 关系</span>
        </div>

        <!-- 图谱 -->
        <div ref="chartRef" class="kg-chart"></div>

        <!-- 一句话画像(后端生成) -->
        <div class="kg-summary" v-if="summary && !fromMock">{{ summary }}</div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { get } from '@/utils/request'

// 模拟数据: Neo4j 连不上时的兜底(演示用)
const mockNodes = [
  { id: '1', name: '人工智能', symbolSize: 60, category: 'AI核心' },
  { id: '2', name: '机器学习', symbolSize: 50, category: '学习方法' },
  { id: '3', name: '深度学习', symbolSize: 50, category: '学习方法' },
  { id: '4', name: '自然语言处理', symbolSize: 45, category: '应用领域' },
  { id: '5', name: '计算机视觉', symbolSize: 45, category: '应用领域' },
  { id: '6', name: '神经网络', symbolSize: 45, category: '学习方法' },
  { id: '7', name: 'Transformer', symbolSize: 40, category: '网络架构' },
  { id: '8', name: 'CNN', symbolSize: 35, category: '网络架构' },
  { id: '9', name: 'RNN', symbolSize: 35, category: '网络架构' },
  { id: '10', name: 'GPT', symbolSize: 40, category: '大模型' },
  { id: '11', name: 'BERT', symbolSize: 38, category: '大模型' },
  { id: '12', name: '图像识别', symbolSize: 35, category: '视觉任务' },
  { id: '13', name: '目标检测', symbolSize: 35, category: '视觉任务' },
  { id: '16', name: '强化学习', symbolSize: 40, category: '学习方法' },
  { id: '18', name: '知识图谱', symbolSize: 45, category: '应用领域' },
  { id: '19', name: '数据挖掘', symbolSize: 38, category: '应用领域' },
  { id: '21', name: '大语言模型', symbolSize: 48, category: '大模型' },
  { id: '22', name: 'PyTorch', symbolSize: 32, category: '框架工具' },
  { id: '23', name: 'TensorFlow', symbolSize: 32, category: '框架工具' },
  { id: '34', name: '图神经网络', symbolSize: 34, category: '网络架构' },
]

const mockLinks = [
  { source: '1', target: '2', label: '包含' },
  { source: '1', target: '3', label: '包含' },
  { source: '1', target: '4', label: '包含' },
  { source: '1', target: '5', label: '包含' },
  { source: '1', target: '16', label: '包含' },
  { source: '2', target: '6', label: '核心方法' },
  { source: '3', target: '7', label: '架构' },
  { source: '3', target: '8', label: '架构' },
  { source: '3', target: '9', label: '架构' },
  { source: '7', target: '10', label: '衍生' },
  { source: '7', target: '11', label: '衍生' },
  { source: '4', target: '21', label: '应用' },
  { source: '5', target: '12', label: '任务' },
  { source: '5', target: '13', label: '任务' },
  { source: '8', target: '12', label: '用于' },
  { source: '1', target: '18', label: '关联' },
  { source: '18', target: '34', label: '方法' },
  { source: '2', target: '19', label: '相关' },
  { source: '3', target: '22', label: '框架' },
  { source: '3', target: '23', label: '框架' },
  { source: '21', target: '10', label: '代表' },
]

const mockCategories = ['AI核心', '学习方法', '应用领域', '网络架构', '大模型', '视觉任务', '框架工具']

// Neo4j 节点类型 → 中文分类名
const TYPE_LABELS = {
  JobDirection: '岗位方向',
  City: '热门城市',
  Education: '学历要求',
  Experience: '经验要求',
  SalaryRange: '薪资分布',
  Salary: '薪资分布',
  Benefit: '常见福利',
  Similar: '相似方向',
}
const typeLabel = (t) => TYPE_LABELS[t] || t || '其他'

// 状态
const chartRef = ref(null)
const loading = ref(false)
const dirLoading = ref(false)
const fromMock = ref(false)
const keyword = ref('')
const directions = ref([])        // 可选岗位方向列表
const summary = ref('')           // 一句话画像(user_value)
const graphNodes = ref([])
const graphLinks = ref([])
const categories = ref([])        // 分类名数组

let chartInstance = null

// 调色板
const PALETTE = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666',
  '#73c0de', '#3ba272', '#fc8452', '#9a60b4',
  '#ea7ccc', '#546e7a',
]

// 加载方向列表
async function fetchDirections() {
  dirLoading.value = true
  try {
    const data = await get('/knowledge-graph/directions')
    directions.value = data || []
    // 默认选第一个(后端按岗位数排过序)
    if (directions.value.length > 0 && !keyword.value) {
      keyword.value = directions.value[0].name
    }
  } catch (err) {
    console.warn('[KnowledgeGraph] 方向列表获取失败:', err)
  } finally {
    dirLoading.value = false
  }
}

// 加载图谱数据
async function fetchGraphData() {
  if (!keyword.value) return
  loading.value = true
  try {
    // request 已拆壳, 拿到的就是业务数据
    const data = await get('/knowledge-graph/direction', { params: { keyword: keyword.value } })

    const center = data.center || {}
    const rawNodes = data.nodes || []
    const rawEdges = data.edges || []

    // 节点:中心大圆,其余按关系占比微调大小
    graphNodes.value = rawNodes.map((n) => ({
      id: n.id,
      name: n.name,
      category: typeLabel(n.type),
      symbolSize: n.id === center.id ? 60 : 36,
      _props: {
        岗位数: n.total_jobs,
        平均薪资K: n.salary_avg_k,
      },
    }))

    graphLinks.value = rawEdges.map((e) => ({
      source: e.source,
      target: e.target,
      label: e.label,
    }))

    // 分类:按节点 type 去重(中心方向排最前)
    const seen = new Set()
    categories.value = []
    rawNodes.forEach((n) => {
      const label = typeLabel(n.type)
      if (!seen.has(label)) {
        seen.add(label)
        categories.value.push(label)
      }
    })

    summary.value = data.user_value || ''
    fromMock.value = false
  } catch (err) {
    console.warn('[KnowledgeGraph] 图谱数据获取失败,使用模拟数据:', err)
    graphNodes.value = mockNodes
    graphLinks.value = mockLinks
    categories.value = mockCategories
    summary.value = ''
    fromMock.value = true
  } finally {
    loading.value = false
    renderChart()
  }
}

// 渲染
function renderChart() {
  if (!chartInstance) return

  const catDefs = categories.value.map((name, i) => ({
    name,
    itemStyle: { color: PALETTE[i % PALETTE.length] },
  }))

  chartInstance.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          if (params.dataType === 'edge') {
            const lbl = params.data.label ? `【${params.data.label}】` : ''
            return `${lbl}${params.data.source} → ${params.data.target}`
          }
          const props = params.data._props
          let extra = ''
          if (props) {
            extra = Object.entries(props)
              .filter(([, v]) => v !== null && v !== undefined && v !== '')
              .map(([k, v]) => `<br/>${k}: ${v}`)
              .join('')
          }
          return `<b>${params.name}</b><br/>分类: ${params.data.category}${extra}`
        },
      },
      legend: {
        show: catDefs.length > 1,
        type: 'scroll',
        orient: 'vertical',
        left: 16,
        top: 48,
        textStyle: { fontSize: 12 },
        data: catDefs.map((c) => ({ name: c.name, icon: 'circle' })),
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: graphNodes.value,
          links: graphLinks.value,
          categories: catDefs,
          roam: true,
          draggable: true,
          label: {
            show: true,
            position: 'right',
            fontSize: 11,
            color: '#333',
          },
          force: {
            repulsion: 400,
            gravity: 0,
            edgeLength: [120, 260],
            layoutAnimation: false,
          },
          lineStyle: {
            color: '#aaa',
            width: 0.8,
            curveness: 0.2,
            opacity: 0.6,
          },
          edgeLabel: {
            show: true,
            fontSize: 9,
            color: '#999',
            formatter: (p) => p.data.label || '',
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 2.5 },
            itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,0,0,0.3)' },
          },
          scaleLimit: { min: 0.3, max: 6 },
        },
      ],
    },
    { notMerge: true }
  )
}

// 自适应
function handleResize() {
  chartInstance?.resize()
}

// 生命周期
onMounted(async () => {
  await nextTick()
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)

  // 先拿方向列表(默认选中第一个),再加载图谱
  await fetchDirections()
  await fetchGraphData()

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style scoped>
.kg-page {
  display: flex;
  flex-direction: column;
}

.kg-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.kg-select {
  width: 240px;
}

.kg-card {
  flex: 1;
}

:deep(.el-card__body) {
  height: 100%;
}

.kg-wrapper {
  width: 100%;
  height: calc(100vh - 300px);
  min-height: 460px;
  position: relative;
  background: #fafbfc;
  border-radius: 6px;
  overflow: hidden;
}

/* 顶部状态栏 */
.kg-toolbar {
  position: absolute;
  top: 10px;
  right: 16px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #666;
  pointer-events: none;
}

.kg-tag {
  background: #fff3e0;
  color: #e65100;
  padding: 2px 10px;
  border-radius: 4px;
  font-weight: 600;
}

.kg-tag.ok {
  background: #e8f5e9;
  color: #2e7d32;
}

.kg-meta {
  color: #999;
  font-size: 12px;
}

/* 图表区域 */
.kg-chart {
  width: 100%;
  height: 100%;
  min-height: inherit;
}

/* 底部一句话画像 */
.kg-summary {
  position: absolute;
  left: 16px;
  bottom: 12px;
  right: 16px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.92);
  border-left: 3px solid #409eff;
  border-radius: 4px;
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  pointer-events: none;
}
</style>
