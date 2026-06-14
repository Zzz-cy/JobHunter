<template>
  <div class="dashboard-page page-container">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon color="#409eff"><DataAnalysis /></el-icon>
        数据分析大盘
      </h1>
      <p class="page-desc">基于已采集招聘数据的多维度可视化分析</p>
    </div>

    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in topStats" :key="stat.label">
        <el-card class="top-stat-card" shadow="hover">
          <div class="top-stat">
            <div class="top-stat-icon" :style="{ background: stat.bg }">
              <el-icon :size="24" color="#fff">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="top-stat-info">
              <div class="top-stat-value">{{ stat.value }}</div>
              <div class="top-stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 1:薪资 + 城市 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>薪资分布</span>
              <el-radio-group v-model="salaryChartType" size="small">
                <el-radio-button label="histogram">直方图</el-radio-button>
                <el-radio-button label="boxplot">箱型图</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="salaryChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>城市职位分布 TOP 10</span>
              <el-tag size="small" type="info" effect="plain">按职位数</el-tag>
            </div>
          </template>
          <div ref="cityChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 2:技能 + 行业 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>热门技能 TOP 15</span>
              <el-radio-group v-model="skillChartType" size="small">
                <el-radio-button label="bar">柱状图</el-radio-button>
                <el-radio-button label="cloud">词云</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="skillChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>行业职位占比</span>
              <el-radio-group v-model="industryChartType" size="small">
                <el-radio-button label="pie">饼图</el-radio-button>
                <el-radio-button label="sunburst">旭日图</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="industryChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 3:趋势 + 学历 -->
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>招聘需求趋势 (近 6 个月)</span>
              <el-tag size="small" type="info" effect="plain">按发布时间</el-tag>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>学历要求分布</span>
            </div>
          </template>
          <div ref="eduChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 4:经验要求雷达图 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>经验要求 × 薪资水平</span>
            </div>
          </template>
          <div ref="expRadarChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="chart-title">
              <span>数据来源占比</span>
            </div>
          </template>
          <div ref="sourceChartRef" class="chart-canvas"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
// import request from '@/utils/request'

// 顶部统计
const topStats = reactive([
  { label: '在招职位', value: '0', icon: 'Briefcase', bg: '#409eff' },
  { label: '入驻公司', value: '0', icon: 'OfficeBuilding', bg: '#67c23a' },
  { label: '覆盖城市', value: '0', icon: 'Location', bg: '#e6a23c' },
  { label: '技能字典', value: '0', icon: 'Cpu', bg: '#f56c6c' }
])

// 图表类型控制
const salaryChartType = ref('histogram')
const skillChartType = ref('bar')
const industryChartType = ref('pie')

// chart DOM 引用
const salaryChartRef = ref(null)
const cityChartRef = ref(null)
const skillChartRef = ref(null)
const industryChartRef = ref(null)
const trendChartRef = ref(null)
const eduChartRef = ref(null)
const expRadarChartRef = ref(null)
const sourceChartRef = ref(null)

// echarts 实例集合
const charts = {}

const initChart = (key, el, option) => {
  if (!el) return
  if (charts[key]) charts[key].dispose()
  const instance = echarts.init(el)
  instance.setOption(option)
  charts[key] = instance
}

const resizeAll = () => {
  Object.values(charts).forEach((c) => c && c.resize())
}

// --- 各图表配置 ---

const renderSalaryChart = () => {
  // TODO: 从后端拉取薪资分布数据
  // const data = await request.get('/stats/salary-distribution')
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ['0-5K', '5-10K', '10-15K', '15-20K', '20-30K', '30-50K', '50K+'],
      axisLabel: { fontSize: 11 }
    },
    yAxis: { type: 'value', name: '职位数' },
    series: [
      {
        type: 'bar',
        data: [/* data */],
        itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] }
      }
    ]
  }
  initChart('salary', salaryChartRef.value, option)
}

const renderCityChart = () => {
  // TODO: const data = await request.get('/stats/city-distribution')
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 80, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: ['北京', '上海', '深圳', '杭州', '广州', '成都', '南京', '武汉', '西安', '苏州'],
      inverse: true
    },
    series: [
      {
        type: 'bar',
        data: [/* data */],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#409eff' },
            { offset: 1, color: '#67c23a' }
          ]),
          borderRadius: [0, 4, 4, 0]
        },
        label: { show: true, position: 'right' }
      }
    ]
  }
  initChart('city', cityChartRef.value, option)
}

const renderSkillChart = () => {
  // TODO: const data = await request.get('/stats/skills/hot', { params: { limit: 15 } })
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 80, right: 30, top: 30, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: ['Python', 'Java', 'JavaScript', 'Go', 'React', 'Vue', 'MySQL', 'Redis', 'Docker', 'K8s', 'Spark', 'LLM', 'AI', '数据建模', '产品'],
      inverse: true
    },
    series: [
      {
        type: 'bar',
        data: [/* data */],
        itemStyle: { color: '#e6a23c', borderRadius: [0, 4, 4, 0] }
      }
    ]
  }
  initChart('skill', skillChartRef.value, option)
}

const renderIndustryChart = () => {
  // TODO: const data = await request.get('/stats/industry-distribution')
  const option = {
    tooltip: { trigger: 'item', formatter: '{a} <br/>{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'middle', textStyle: { fontSize: 11 } },
    series: [
      {
        name: '行业占比',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        data: [
          { name: '互联网/IT', value: 0 },
          { name: '金融', value: 0 },
          { name: '制造业', value: 0 },
          { name: '教育', value: 0 },
          { name: '医疗', value: 0 },
          { name: '其他', value: 0 }
        ],
        label: { fontSize: 11 }
      }
    ]
  }
  initChart('industry', industryChartRef.value, option)
}

const renderTrendChart = () => {
  // TODO: const data = await request.get('/stats/trend', { params: { months: 6 } })
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增职位', '下架职位'] },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['1月', '2月', '3月', '4月', '5月', '6月']
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '新增职位',
        type: 'line',
        smooth: true,
        data: [],
        areaStyle: { opacity: 0.3 },
        itemStyle: { color: '#409eff' }
      },
      {
        name: '下架职位',
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color: '#f56c6c' }
      }
    ]
  }
  initChart('trend', trendChartRef.value, option)
}

const renderEduChart = () => {
  // TODO: const data = await request.get('/stats/education-distribution')
  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['35%', '60%'],
        data: [
          { name: '不限', value: 0 },
          { name: '大专', value: 0 },
          { name: '本科', value: 0 },
          { name: '硕士', value: 0 },
          { name: '博士', value: 0 }
        ],
        label: { formatter: '{b}: {d}%', fontSize: 11 }
      }
    ]
  }
  initChart('edu', eduChartRef.value, option)
}

const renderExpRadarChart = () => {
  // TODO: const data = await request.get('/stats/experience-salary')
  const option = {
    tooltip: {},
    radar: {
      indicator: [
        { name: '应届', max: 50 },
        { name: '1-3年', max: 50 },
        { name: '3-5年', max: 50 },
        { name: '5-10年', max: 50 },
        { name: '10年+', max: 50 }
      ],
      radius: '60%'
    },
    series: [
      {
        type: 'radar',
        data: [
          { value: [0, 0, 0, 0, 0], name: '平均薪资(K)' }
        ],
        areaStyle: { opacity: 0.3 }
      }
    ]
  }
  initChart('expRadar', expRadarChartRef.value, option)
}

const renderSourceChart = () => {
  // TODO: const data = await request.get('/stats/source-distribution')
  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: '60%',
        data: [
          { name: 'Boss直聘', value: 0 },
          { name: '猎聘', value: 0 },
          { name: '官网直招', value: 0 }
        ],
        label: { formatter: '{b}: {c} ({d}%)', fontSize: 11 }
      }
    ]
  }
  initChart('source', sourceChartRef.value, option)
}

// 加载所有数据并渲染
const loadAllCharts = async () => {
  await nextTick()
  // TODO: 拉取顶部统计数据
  // const stats = await request.get('/stats/overview')
  // topStats[0].value = stats.jobCount
  // topStats[1].value = stats.companyCount
  // topStats[2].value = stats.cityCount
  // topStats[3].value = stats.skillCount

  renderSalaryChart()
  renderCityChart()
  renderSkillChart()
  renderIndustryChart()
  renderTrendChart()
  renderEduChart()
  renderExpRadarChart()
  renderSourceChart()
}

// 图表类型切换时重渲染
watch(salaryChartType, renderSalaryChart)
watch(skillChartType, renderSkillChart)
watch(industryChartType, renderIndustryChart)

onMounted(() => {
  loadAllCharts()
  window.addEventListener('resize', resizeAll)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAll)
  Object.values(charts).forEach((c) => c && c.dispose())
})
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 26px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.page-desc {
  color: #909399;
  font-size: 14px;
}

.stat-row {
  margin-bottom: 16px;
}

.top-stat-card {
  padding: 8px;
}

.top-stat {
  display: flex;
  align-items: center;
  gap: 12px;
}

.top-stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.top-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.top-stat-label {
  color: #909399;
  font-size: 13px;
  margin-top: 2px;
}

.chart-card {
  margin-bottom: 16px;
}

.chart-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.chart-canvas {
  height: 320px;
  width: 100%;
}
</style>
