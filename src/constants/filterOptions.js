// 求职筛选共享选项: 引导建档页与找职位页共用, 防止两处口径漂移
// 薪资档位 value 与后端 OnboardingSchema 的 Literal 枚举一致

// 城市选项(与找职位页城市下拉一致)
export const cityOptions = ['北京', '上海', '深圳', '广州', '杭州', '成都', '南京', '武汉', '西安', '苏州', '其他']

// 薪资档位选项(label 展示文案 / value 筛选值)
export const salaryOptions = [
  { label: '10K 以下', value: '0-10' },
  { label: '10-20K', value: '10-20' },
  { label: '20-30K', value: '20-30' },
  { label: '30-50K', value: '30-50' },
  { label: '50K 以上', value: '50-' }
]
