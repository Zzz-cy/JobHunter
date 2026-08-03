/**
 * 格式化工具: 统一处理"数据库存的值 → 前端展示的值"
 *
 * 重要约定:
 *   - 数据库 salary_min/max 存的是"元"(如 25000)
 *   - 前端展示用"K"(如 25K), 所以要除以 1000
 */

/**
 * 把薪资(元)转成 K 展示文本。
 *
 * @param {Object} job  职位对象, 至少包含 salary_min / salary_max / salary_unit / salary_months
 * @returns {string}    形如 "25-50K·16薪" / "25K" / "200元/天" / "薪资面议"
 *
 * 用法:
 *   formatSalary(job)  // 在 JobCard / JobDetail / Profile 里都能用
 */
export function formatSalary(job) {
  if (!job) return '薪资面议'

  const min = job.salary_min
  const max = job.salary_max

  // 都没有 → 薪资面议
  if (!min && !max) return '薪资面议'

  // 单位转换: 数据库存的是"元"
  // month → 展示成 K (除以1000)
  // day   → 展示成 元/天 (不除, 数字小)
  // year  → 展示成 K/年 (除以1000)
  if (job.salary_unit === 'day') {
    const unit = '元/天'
    if (min && max) return `${min}-${max}${unit}`
    return `${min || max}${unit}`
  }

  // month / year 统一转 K
  const minK = min ? Math.round(min / 1000) : null
  const maxK = max ? Math.round(max / 1000) : null
  const unit = job.salary_unit === 'year' ? 'K/年' : 'K'

  if (minK && maxK) {
    return `${minK}-${maxK}${unit}${job.salary_months ? `·${job.salary_months}薪` : ''}`
  }
  return `${minK || maxK}${unit}`
}
