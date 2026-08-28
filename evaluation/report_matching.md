# 人岗匹配准确率评测报告

- 评测时间: 2026-08-28 17:02:52
- 样本: 10/10 份简历, 每份取 Top10 推荐

## 总体指标

| 指标 | 定义 | 数值 |
|---|---|---|
| **M1 匹配命中率** | Top10 岗位技能与简历技能交集达阈值的占比 | **88.0%** (88/100) |
| M2 平均技能重合度 | 岗位技能∩简历技能 / 简历技能数 | 74.7% |
| M3 Top1 相关率 | 排名第 1 岗位与简历相关的简历占比 | 100.0% (10/10) |

## 每份简历明细

### 李伟(Python 后端工程师) 命中率 100% · 重合度 100% · Top1相关 · 策略 rag

简历技能: Django, Docker, MySQL, Python, Redis

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | Python开发 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 2 | Python 后端开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 3 | python 工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 4 | python工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 5 | Python开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 6 | Python开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 7 | Python开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 8 | Python开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 9 | Python开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |
| 10 | Python开发工程师 | 90.0 | Django, Docker, MySQL, Python, Redis | 100% | ✅ |

### 王芳(前端开发工程师) 命中率 0% · 重合度 25% · Top1相关 · 策略 rag

简历技能: CSS, JavaScript, React, Vue

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 2 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 3 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 4 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 5 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 6 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 7 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 8 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 9 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |
| 10 | 前端开发人员 | 90.0 | Vue | 25% | ❌ |

### 张鹏(Java 后端开发工程师) 命中率 100% · 重合度 100% · Top1相关 · 策略 rag

简历技能: Java, Kafka, MySQL, Redis, Spring Boot

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | Java技术专家 | 95.0 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 2 | Java开发工程师 | 95.0 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 3 | Java | 88.05 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 4 | Java | 88.05 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 5 | Java | 88.05 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 6 | Java | 88.04 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 7 | C++/Java 后端开发 | 87.86 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 8 | Java开发工程师 | 87.58 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 9 | Java开发工程师 | 87.58 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |
| 10 | Java开发工程师 | 87.58 | Java, Kafka, MySQL, Redis, Spring Boot | 100% | ✅ |

### 陈静(数据分析师) 命中率 100% · 重合度 74% · Top1相关 · 策略 rag

简历技能: Excel, Python, SQL, Tableau, 数据分析

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 数据分析 | 86.23 | Python, SQL, 数据分析 | 60% | ✅ |
| 2 | 招聘数据分析-增长 | 85.29 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |
| 3 | 数据分析 | 85.26 | Python, SQL, 数据分析 | 60% | ✅ |
| 4 | 经营分析实习生 | 85.01 | Python, SQL, 数据分析 | 60% | ✅ |
| 5 | 招聘用户与数据分析 | 84.75 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |
| 6 | 招聘数据分析/商业分析 | 84.61 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |
| 7 | 招聘数据分析/商业分析 | 84.6 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |
| 8 | 招聘数据分析/商业分析 | 84.6 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |
| 9 | 招聘数据分析/商业分析/业务分析 | 84.48 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |
| 10 | 招聘商业分析师&amp;数据分析师 | 84.21 | Python, SQL, Tableau, 数据分析 | 80% | ✅ |

### 刘洋(算法工程师) 命中率 100% · 重合度 100% · Top1相关 · 策略 rag

简历技能: PyTorch, Python, TensorFlow, 机器学习, 深度学习

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 27届秋招岗位-AI工程师（地点open） | 90.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 2 | AI应用工程师-AI系统软件 | 90.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 3 | 算法工程师 | 85.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 4 | 具身智能算法实习生 | 85.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 5 | 推荐算法 | 85.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 6 | 机器学习研究员(2027届) | 80.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 7 | 模型算法工程师（2027届） | 80.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 8 | 算法工程师（27届） | 80.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 9 | 算法工程师-棋牌 | 80.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |
| 10 | AI应用工程师 | 80.0 | PyTorch, Python, TensorFlow, 机器学习, 深度学习 | 100% | ✅ |

### 赵磊(测试工程师) 命中率 100% · 重合度 100% · Top1相关 · 策略 rag

简历技能: Linux, Python, Selenium, 自动化测试

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 测试工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 2 | 测试工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 3 | 软件测试��程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 4 | 测试开发工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 5 | 测试开发工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 6 | 测试开发工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 7 | 测试开发工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 8 | 测试开发工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 9 | 高级测试工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |
| 10 | 高级/资深测试工程师 | 95.0 | Linux, Python, Selenium, 自动化测试 | 100% | ✅ |

### 孙悦(大数据开发工程师) 命中率 100% · 重合度 68% · Top1相关 · 策略 rag

简历技能: Flink, Hadoop, Kafka, SQL, Spark

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 数据开发工程师实习生 | 95.0 | Flink, Hadoop, Kafka, SQL, Spark | 100% | ✅ |
| 2 | 大数据开发工程师 | 92.0 | Hadoop, SQL, Spark | 60% | ✅ |
| 3 | 大数据开发工程师 | 92.0 | Hadoop, SQL, Spark | 60% | ✅ |
| 4 | 大数据开发工程师 | 92.0 | Hadoop, SQL, Spark | 60% | ✅ |
| 5 | 大数据开发工程师 | 92.0 | Hadoop, SQL, Spark | 60% | ✅ |
| 6 | 数据开发实习生 | 90.0 | Flink, Hadoop, Kafka, SQL, Spark | 100% | ✅ |
| 7 | 实习生-大数据开发实习生-贵阳 | 90.0 | Hadoop, Kafka, Spark | 60% | ✅ |
| 8 | 资深数据研发工程师/技术专家 | 90.0 | Hadoop, SQL, Spark | 60% | ✅ |
| 9 | 招聘数据统计 | 90.0 | Hadoop, SQL, Spark | 60% | ✅ |
| 10 | 招聘数据统计 | 90.0 | Hadoop, SQL, Spark | 60% | ✅ |

### 周杰(运维开发工程师) 命中率 100% · 重合度 74% · Top1相关 · 策略 rag

简历技能: Docker, Git, Kubernetes, Linux, Shell

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 公有云运维工程师 | 90.0 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 2 | 高级运维专家-电商SRE | 90.0 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 3 | 混合云专线运维工程师 | 90.0 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 4 | SRE工程师/专家 — 音视频 | 90.0 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 5 | k8s高级研发工程师/技术专家 | 85.18 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 6 | support engineer—LInux&network | 85.0 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 7 | 资深业务DBA(MySQL) | 85.0 | Docker, Kubernetes, Linux, Shell | 80% | ✅ |
| 8 | 持续集成工程师 | 85.0 | Docker, Git, Linux | 60% | ✅ |
| 9 | 高级运维工程师 | 85.0 | Docker, Kubernetes, Linux | 60% | ✅ |
| 10 | python开发工程师 | 85.0 | Docker, Git, Linux | 60% | ✅ |

### 吴敏(产品经理) 命中率 100% · 重合度 33% · Top1相关 · 策略 rag

简历技能: 产品经理, 需求分析, 项目管理

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 软件产品经理 | 90.0 | 产品经理 | 33% | ✅ |
| 2 | 产品经理 | 90.0 | 产品经理 | 33% | ✅ |
| 3 | 产品经理 | 85.0 | 产品经理 | 33% | ✅ |
| 4 | 工程产品助理 | 85.0 | 产品经理 | 33% | ✅ |
| 5 | 工程产品助理 | 85.0 | 产品经理 | 33% | ✅ |
| 6 | 互联网产品经理 | 85.0 | 产品经理 | 33% | ✅ |
| 7 | 软件产品经理实习生 | 80.0 | 产品经理 | 33% | ✅ |
| 8 | 软件产品经理实习生 | 80.0 | 产品经理 | 33% | ✅ |
| 9 | 产品经理 | 80.0 | 产品经理 | 33% | ✅ |
| 10 | 产品助理 | 80.0 | 产品经理 | 33% | ✅ |

### 郑强(C++ 开发工程师(应届)) 命中率 80% · 重合度 72% · Top1相关 · 策略 rag

简历技能: C++, Git, 数据结构, 算法

| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |
|---|---|---|---|---|---|
| 1 | 软件开发实习生 | 90.0 | C++, 数据结构, 算法 | 75% | ✅ |
| 2 | C++ | 85.0 | C++, Git, 数据结构, 算法 | 100% | ✅ |
| 3 | C++（北京） | 85.0 | C++, Git, 数据结构, 算法 | 100% | ✅ |
| 4 | c++开发 | 85.0 | C++, 数据结构, 算法 | 75% | ✅ |
| 5 | 软件开发工程师 | 85.0 | C++, 数据结构, 算法 | 75% | ✅ |
| 6 | C/C++服务端研发工程师 | 85.0 | C++, Git, 数据结构, 算法 | 100% | ✅ |
| 7 | C++开发实习生（Android系统方向） | 80.0 | C++ | 25% | ❌ |
| 8 | 三维软件开发实习生 | 80.0 | C++, Git, 数据结构, 算法 | 100% | ✅ |
| 9 | c++实习生 | 75.0 | C++ | 25% | ❌ |
| 10 | 高性能计算实习生 | 75.0 | C++, 算法 | 50% | ✅ |
