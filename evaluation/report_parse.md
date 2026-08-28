# 简历解析准确率评测报告

- 评测时间: 2026-08-28 16:59:28
- 样本数量: 10 份(解析成功 10 份)
- 评分规则: 标量字段允许 age/work_years ±1, phone 比后 4 位, skills 召回≥0.8 记通过

## 总体指标

| 指标 | 数值 |
|---|---|
| **综合字段准确率** | **100.0%** |
| 标量字段准确率 | 100.0% (80/80) |
| 技能字段通过率 | 10/10 |
| 技能平均召回率 | 94.0% |
| 技能平均精确率 | 96.0% |

## 分字段准确率

| 字段 | 准确率 |
|---|---|
| name | 100.0% (10/10) |
| gender | 100.0% (10/10) |
| age | 100.0% (10/10) |
| phone | 100.0% (10/10) |
| email | 100.0% (10/10) |
| city | 100.0% (10/10) |
| work_years | 100.0% (10/10) |
| education | 100.0% (10/10) |

## 每份简历明细

### 李伟(Python 后端工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 李伟 | 李伟 | ✅ |
| gender | 0 | 0 | ✅ |
| age | 28 | 28 | ✅ |
| phone | 13812340001 | 13812340001 | ✅ |
| email | liwei@example.com | liwei@example.com | ✅ |
| city | 北京 | 北京 | ✅ |
| work_years | 5 | 5 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['Django', 'Docker', 'MySQL', 'Python', 'Redis'] | ['Django', 'Docker', 'Python', 'Redis', 'SQL'] | ✅ 召回0.8 |

### 王芳(前端开发工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 王芳 | 王芳 | ✅ |
| gender | 1 | 1 | ✅ |
| age | 26 | 26 | ✅ |
| phone | 13912340002 | 13912340002 | ✅ |
| email | wangfang@example.com | wangfang@example.com | ✅ |
| city | 上海 | 上海 | ✅ |
| work_years | 3 | 3 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['CSS', 'JavaScript', 'React', 'Vue'] | ['CSS', 'JavaScript', 'React', 'Vue'] | ✅ 召回1.0 |

### 张鹏(Java 后端开发工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 张鹏 | 张鹏 | ✅ |
| gender | 0 | 0 | ✅ |
| age | 31 | 31 | ✅ |
| phone | 13612340003 | 13612340003 | ✅ |
| email | zhangpeng@example.com | zhangpeng@example.com | ✅ |
| city | 深圳 | 深圳 | ✅ |
| work_years | 7 | 7 | ✅ |
| education | 硕士 | 硕士 | ✅ |
| skills | ['Java', 'Kafka', 'MySQL', 'Redis', 'Spring Boot'] | ['Java', 'Kafka', 'Redis', 'SQL', 'Spring Boot'] | ✅ 召回0.8 |

### 陈静(数据分析师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 陈静 | 陈静 | ✅ |
| gender | 1 | 1 | ✅ |
| age | 27 | 27 | ✅ |
| phone | 13712340004 | 13712340004 | ✅ |
| email | chenjing@example.com | chenjing@example.com | ✅ |
| city | 杭州 | 杭州 | ✅ |
| work_years | 4 | 4 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['Excel', 'Python', 'SQL', 'Tableau', '数据分析'] | ['Excel', 'Python', 'SQL', 'Tableau', '数据分析'] | ✅ 召回1.0 |

### 刘洋(算法工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 刘洋 | 刘洋 | ✅ |
| gender | 0 | 0 | ✅ |
| age | 29 | 29 | ✅ |
| phone | 13512340005 | 13512340005 | ✅ |
| email | liuyang@example.com | liuyang@example.com | ✅ |
| city | 北京 | 北京 | ✅ |
| work_years | 6 | 6 | ✅ |
| education | 硕士 | 硕士 | ✅ |
| skills | ['PyTorch', 'Python', 'TensorFlow', '机器学习', '深度学习'] | ['PyTorch', 'Python', 'TensorFlow', '机器学习', '深度学习'] | ✅ 召回1.0 |

### 赵磊(测试工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 赵磊 | 赵磊 | ✅ |
| gender | 0 | 0 | ✅ |
| age | 25 | 25 | ✅ |
| phone | 15812340006 | 15812340006 | ✅ |
| email | zhaolei@example.com | zhaolei@example.com | ✅ |
| city | 成都 | 成都 | ✅ |
| work_years | 3 | 3 | ✅ |
| education | 大专 | 大专 | ✅ |
| skills | ['Linux', 'Python', 'Selenium', '自动化测试'] | ['Linux', 'Python', 'Selenium', '自动化测试'] | ✅ 召回1.0 |

### 孙悦(大数据开发工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 孙悦 | 孙悦 | ✅ |
| gender | 1 | 1 | ✅ |
| age | 28 | 28 | ✅ |
| phone | 15012340007 | 15012340007 | ✅ |
| email | sunyue@example.com | sunyue@example.com | ✅ |
| city | 广州 | 广州 | ✅ |
| work_years | 5 | 5 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['Flink', 'Hadoop', 'Kafka', 'SQL', 'Spark'] | ['Flink', 'Hadoop', 'Kafka', 'SQL', 'Spark'] | ✅ 召回1.0 |

### 周杰(运维开发工程师)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 周杰 | 周杰 | ✅ |
| gender | 0 | 0 | ✅ |
| age | 27 | 27 | ✅ |
| phone | 15112340008 | 15112340008 | ✅ |
| email | zhoujie@example.com | zhoujie@example.com | ✅ |
| city | 北京 | 北京 | ✅ |
| work_years | 4 | 4 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['Docker', 'Git', 'Kubernetes', 'Linux', 'Shell'] | ['Docker', 'Git', 'Kubernetes', 'Linux'] | ✅ 召回0.8 |

### 吴敏(产品经理)

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 吴敏 | 吴敏 | ✅ |
| gender | 1 | 1 | ✅ |
| age | 29 | 29 | ✅ |
| phone | 18612340009 | 18612340009 | ✅ |
| email | wumin@example.com | wumin@example.com | ✅ |
| city | 上海 | 上海 | ✅ |
| work_years | 6 | 6 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['产品经理', '需求分析', '项目管理'] | ['产品经理', '需求分析', '项目管理'] | ✅ 召回1.0 |

### 郑强(C++ 开发工程师(应届))

| 字段 | 期望 | 实际 | 通过 |
|---|---|---|---|
| name | 郑强 | 郑强 | ✅ |
| gender | 0 | 0 | ✅ |
| age | 23 | 23 | ✅ |
| phone | 13412340010 | 13412340010 | ✅ |
| email | zhengqiang@example.com | zhengqiang@example.com | ✅ |
| city | 武汉 | 武汉 | ✅ |
| work_years | 0 | 0 | ✅ |
| education | 本科 | 本科 | ✅ |
| skills | ['C++', 'Git', '数据结构', '算法'] | ['C++', 'Git', '数据结构', '算法'] | ✅ 召回1.0 |
