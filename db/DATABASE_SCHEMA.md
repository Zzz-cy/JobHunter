# JobHunter 数据库字段说明文档

> **数据库**：MySQL `jobhunter` (utf8mb4 / utf8mb4_unicode_ci)
> **共 15 张表**：分 5 层 — 字典层 / 主体层 / 行为层 / 采集层
> **生成时间**：2026-06-13

---

## 目录

- [一、字典层](#一字典层)
  - [1.1 `skills` 技能字典](#11-skills-技能字典)
  - [1.2 `industries` 行业字典](#12-industries-行业字典)
- [二、主体层](#二主体层)
  - [2.1 `users` 系统用户](#21-users-系统用户)
  - [2.2 `resumes` 简历主表](#22-resumes-简历主表)
  - [2.3 `resume_skills` 简历技能关联](#23-resume_skills-简历技能关联)
  - [2.4 `resume_experiences` 工作经历](#24-resume_experiences-工作经历)
  - [2.5 `resume_educations` 教育经历](#25-resume_educations-教育经历)
  - [2.6 `companies` 公司信息](#26-companies-公司信息)
  - [2.7 `jobs` 职位主表](#27-jobs-职位主表)
  - [2.8 `job_skills` 职位技能关联](#28-job_skills-职位技能关联)
- [三、行为层](#三行为层)
  - [3.1 `applications` 用户-职位关系](#31-applications-用户-职位关系)
  - [3.2 `recommendations` 推荐流水](#32-recommendations-推荐流水)
  - [3.3 `chat_history` AI 对话历史](#33-chat_history-ai-对话历史)
- [四、采集层](#四采集层)
  - [4.1 `crawl_sources` 数据源配置](#41-crawl_sources-数据源配置)
  - [4.2 `crawl_tasks` 爬虫任务记录](#42-crawl_tasks-爬虫任务记录)
- [五、通用约定](#五通用约定)
- [六、ER 关系图](#六er-关系图)

---

## 一、字典层

字典层是整个系统的"标准化基石"，解决多源数据命名不一致问题（如 Boss直聘叫「Python3」，拉勾叫「Python」，官网叫「Py」实际上是同一技能）。

### 1.1 `skills` 技能字典

**用途**：标准化技能库，与 Neo4j 中的 Skill 节点一一对应，是匹配算法的核心数据源。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键，内部使用 |
| `skill_code` | VARCHAR(64) | NO | — | **UNI** | 对外编码（雪花算法/UUID），不暴露内部自增 ID，**与 Neo4j Skill 节点的 id 一致** |
| `name` | VARCHAR(128) | NO | — | **UNI** | 标准化技能名（如 `Python`），**整个系统的"官方叫法"**，不可重复 |
| `alias` | VARCHAR(255) | YES | NULL | — | 别称，逗号分隔（如 `py,Python3,python3.x`），NER 抽取时用于实体归一 |
| `category` | VARCHAR(64) | YES | NULL | MUL | 分类：`语言` / `框架` / `工具` / `方向` / `软技能` |
| `is_hot` | TINYINT(1) | NO | 0 | MUL | 是否热门技能（0=否，1=是），用于"热门技能榜"可视化 |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间，自动维护 |

**索引说明**：
- `uk_skill_code`：对外编码唯一，便于 API 查询
- `uk_skill_name`：标准化名唯一，防止字典重复
- `idx_skill_category`：分类聚合查询（如"统计所有语言类技能"）
- `idx_skill_hot`：热门技能榜热路径

**示例数据**：
```
id=1, skill_code='SK_PY', name='Python', alias='py,python3', category='语言', is_hot=1
id=7, skill_code='SK_REACT', name='React', alias='reactjs', category='框架', is_hot=1
```

---

### 1.2 `industries` 行业字典

**用途**：行业层级字典，支持 ECharts 钻取图（如"互联网 → 互联网/研发"二级钻取）。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | INT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `code` | VARCHAR(32) | NO | — | **UNI** | 行业编码（如 `IT`、`IT-RD`），用于业务表关联 |
| `name` | VARCHAR(64) | NO | — | — | 行业名称（如 `互联网/IT`） |
| `parent_id` | INT UNSIGNED | YES | NULL | MUL | 父级行业 ID，**自引用实现层级** |
| `level` | TINYINT | NO | 1 | — | 层级（1=一级行业，2=二级行业） |

**索引说明**：
- `uk_industry_code`：编码唯一
- `idx_industry_parent`：按父级查询子行业（构建层级树）

**层级示例**：
```
level=1  IT       "互联网/IT"   parent_id=NULL
  └─ level=2  IT-RD    "研发"      parent_id=1(IT)
  └─ level=2  IT-DATA  "数据"      parent_id=1(IT)
  └─ level=2  IT-PM    "产品"      parent_id=1(IT)
```

---

## 二、主体层

主体层存储系统核心业务实体（用户、简历、公司、职位）。

### 2.1 `users` 系统用户

**用途**：系统用户账号表，支持求职者和后台管理员两种角色。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `user_code` | VARCHAR(64) | NO | — | **UNI** | 对外编码，URL 中使用（避免暴露自增 ID 被估算用户量） |
| `phone` | VARCHAR(20) | YES | NULL | **UNI** | 手机号，**加密存储**（应用层 AES），唯一 |
| `email` | VARCHAR(128) | YES | NULL | **UNI** | 邮箱，唯一 |
| `password_hash` | VARCHAR(128) | NO | — | — | bcrypt 哈希（长度 ≥60，预留空间） |
| `nickname` | VARCHAR(64) | YES | NULL | — | 昵称，前端展示用 |
| `avatar_url` | VARCHAR(512) | YES | NULL | — | 头像 URL |
| `role` | VARCHAR(16) | NO | 'user' | MUL | 角色：`user`（求职者）/ `admin`（管理员），预留 RBAC 扩展 |
| `last_login_at` | DATETIME | YES | NULL | — | 最近登录时间，用于活跃度统计 |
| `is_deleted` | TINYINT(1) | NO | 0 | — | 软删除标记（0=正常，1=已删除） |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 注册时间 |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间 |

**索引说明**：
- `uk_user_phone` / `uk_user_email`：登录查询走唯一索引，O(1)
- `idx_user_role`：管理后台"用户列表按角色筛选"

**安全设计**：
- `phone` 加密存储：即使数据库泄露，也无法直接获取手机号
- `password_hash` 用 bcrypt：抗彩虹表攻击

---

### 2.2 `resumes` 简历主表

**用途**：简历元信息表，详细经历（工作/教育/技能）拆分到子表。一份简历 = 1 条主表记录 + N 条子表记录。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `resume_code` | VARCHAR(64) | NO | — | **UNI** | 对外编码 |
| `user_id` | BIGINT UNSIGNED | NO | — | MUL | 所属用户 ID |
| `name` | VARCHAR(64) | NO | — | — | 姓名 |
| `gender` | TINYINT | YES | NULL | — | 性别（0=男，1=女） |
| `age` | INT | YES | NULL | — | 年龄 |
| `city` | VARCHAR(64) | YES | NULL | MUL | 现居城市 |
| `phone` | VARCHAR(20) | YES | NULL | — | 简历上的联系方式 |
| `email` | VARCHAR(128) | YES | NULL | — | 简历上的邮箱 |
| `source_type` | VARCHAR(16) | NO | 'pdf' | — | 简历来源类型：`pdf` / `image` / `manual`（手动填写） |
| `file_url` | VARCHAR(512) | YES | NULL | — | 原始文件 URL（OSS/本地路径） |
| `parse_status` | VARCHAR(16) | NO | 'pending' | MUL | 解析状态机：`pending` → `parsing` → `done` / `failed` |
| `parse_error` | VARCHAR(512) | YES | NULL | — | 解析失败原因（便于排查） |
| `work_years` | INT | YES | NULL | — | 总工作年限 |
| `education` | VARCHAR(16) | YES | NULL | — | 最高学历：`大专` / `本科` / `硕士` / `博士` |
| `expect_salary_min` | INT | YES | NULL | — | 期望薪资下限（元/月） |
| `expect_salary_max` | INT | YES | NULL | — | 期望薪资上限（元/月） |
| `expect_city` | VARCHAR(64) | YES | NULL | — | 期望工作城市 |
| `expect_job` | VARCHAR(128) | YES | NULL | — | 期望岗位（如"高级 Python 工程师"） |
| `overall_score` | DECIMAL(5,2) | YES | NULL | — | 简历完整度评分（0-100），影响推荐权重 |
| `parsed_raw` | JSON | YES | NULL | — | **OCR/解析原始结果**，调试用，后续 NER 输入 |
| `is_deleted` | TINYINT(1) | NO | 0 | — | 软删除 |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间 |

**索引说明**：
- `uk_resume_code`：对外编码唯一
- `idx_resume_user`：查询"某用户的所有简历"
- `idx_resume_status`：后台监控"待解析简历队列"
- `idx_resume_city`：按城市筛选简历
- `idx_resume_created`：按创建时间排序

**解析状态机**：
```
pending ──upload──> parsing ──success──> done
                       │
                       └────failed<──── 重试3次后
```

**`parsed_raw` JSON 字段作用**：
- OCR 原始返回先存这里，避免解析失败丢数据
- 后续 NER / 星火抽取从这读取
- 调试时可以回溯"为什么这个字段抽错了"

---

### 2.3 `resume_skills` 简历技能关联

**用途**：简历与技能的多对多关联表，是匹配算法的核心输入。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `resume_id` | BIGINT UNSIGNED | NO | — | MUL | 简历 ID |
| `skill_id` | BIGINT UNSIGNED | NO | — | MUL | 技能 ID（关联 `skills.id`） |
| `proficiency` | TINYINT | NO | 3 | — | 熟练度（1-5），匹配评分权重 |
| `years` | DECIMAL(4,1) | YES | NULL | — | 使用年限（如 3.5 年） |

**索引说明**：
- `uk_resume_skill`：(resume_id, skill_id) 联合唯一，防止重复
- `idx_rs_skill`：反向查询"某技能被多少简历掌握"

**匹配评分公式核心输入**：
```
match_score = Σ (skill.weight × user.proficiency × time_decay(years))
```

---

### 2.4 `resume_experiences` 工作经历

**用途**：简历的工作经历明细，一份简历可有多段。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `resume_id` | BIGINT UNSIGNED | NO | — | MUL | 所属简历 ID |
| `company_name` | VARCHAR(128) | NO | — | — | 公司名称 |
| `title` | VARCHAR(128) | YES | NULL | — | 职位名称（如"高级 Java 工程师"） |
| `start_date` | DATE | YES | NULL | — | 入职日期 |
| `end_date` | DATE | YES | NULL | — | 离职日期（在职则 NULL） |
| `description` | TEXT | YES | NULL | — | 工作内容描述 |
| `is_current` | TINYINT(1) | NO | 0 | — | 是否当前在职（0=否，1=是） |

**索引说明**：
- `idx_rexp_resume`：按简历查询所有工作经历

---

### 2.5 `resume_educations` 教育经历

**用途**：简历的教育经历明细。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `resume_id` | BIGINT UNSIGNED | NO | — | MUL | 所属简历 ID |
| `school` | VARCHAR(128) | NO | — | — | 学校名称 |
| `major` | VARCHAR(128) | YES | NULL | — | 专业 |
| `degree` | VARCHAR(32) | YES | NULL | — | 学历：`大专` / `本科` / `硕士` / `博士` |
| `start_date` | DATE | YES | NULL | — | 入学日期 |
| `end_date` | DATE | YES | NULL | — | 毕业日期 |

**索引说明**：
- `idx_redu_resume`：按简历查询教育经历

---

### 2.6 `companies` 公司信息

**用途**：公司主表，爬虫产物之一。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `company_code` | VARCHAR(64) | NO | — | **UNI** | 对外编码 |
| `name` | VARCHAR(128) | NO | — | **UNI**（联合） | 公司全称 |
| `short_name` | VARCHAR(64) | YES | NULL | — | 公司简称（如"阿里"） |
| `industry_code` | VARCHAR(32) | YES | NULL | MUL | 行业编码（关联 `industries.code`） |
| `size` | VARCHAR(32) | YES | NULL | — | 公司规模：`0-20` / `20-99` / `100-499` / `500-999` / `1000-9999` / `10000+` |
| `stage` | VARCHAR(32) | YES | NULL | — | 融资阶段：`未融资` / `天使轮` / `A轮` / ... / `已上市` |
| `city` | VARCHAR(64) | YES | NULL | MUL | 所在城市 |
| `district` | VARCHAR(64) | YES | NULL | — | 所在区县 |
| `address` | VARCHAR(255) | YES | NULL | — | 详细地址 |
| `logo_url` | VARCHAR(512) | YES | NULL | — | Logo URL |
| `website` | VARCHAR(255) | YES | NULL | — | 官网 URL |
| `welfare` | JSON | YES | NULL | — | 福利标签数组（如 `["六险一金","免费餐","弹性工作"]`） |
| `description` | TEXT | YES | NULL | — | 公司介绍 |
| `source` | VARCHAR(32) | NO | 'boss' | — | 数据来源：`boss` / `liepin` / `official`（官网） |
| `source_url` | VARCHAR(512) | YES | NULL | — | 原始页面 URL，用于回溯 |
| `is_deleted` | TINYINT(1) | NO | 0 | — | 软删除 |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间 |

**索引说明**：
- `uk_company_code`：对外编码唯一
- `uk_company_name_source`：(name, source) 联合唯一，**同一公司名 + 不同来源是不同记录**，避免覆盖
- `idx_company_industry`：按行业筛选公司
- `idx_company_city`：按城市筛选

**实体对齐策略**：MySQL 中按 (name, source) 去重；Neo4j 中通过 `company_code` 做实体合并。

---

### 2.7 `jobs` 职位主表

**用途**：爬虫核心产物，存储招聘职位信息。**最复杂的表**。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `job_code` | VARCHAR(64) | NO | — | **UNI** | 对外编码 |
| `company_id` | BIGINT UNSIGNED | YES | NULL | MUL | 所属公司 ID |
| `title` | VARCHAR(255) | NO | — | — | 职位名称 |
| `department` | VARCHAR(128) | YES | NULL | — | 部门 |
| `city` | VARCHAR(64) | YES | NULL | MUL | 工作城市 |
| `district` | VARCHAR(64) | YES | NULL | — | 工作区县 |
| `experience_req` | VARCHAR(32) | YES | NULL | — | 经验要求（如 `3-5年` / `应届` / `不限`） |
| `education_req` | VARCHAR(32) | YES | NULL | — | 学历要求 |
| `salary_min` | INT | YES | NULL | MUL | 薪资下限（元/月） |
| `salary_max` | INT | YES | NULL | MUL | 薪资上限（元/月） |
| `salary_unit` | VARCHAR(8) | NO | 'month' | — | 薪资单位：`month`（月）/ `day`（日，实习）/ `year`（年，外包） |
| `salary_months` | TINYINT | YES | NULL | — | 几薪（如 13、14），影响年薪计算 |
| `job_type` | VARCHAR(16) | NO | 'full' | — | 职位类型：`full`（全职）/ `part`（兼职）/ `intern`（实习） |
| `description` | TEXT | YES | NULL | — | JD 正文（含 HTML 标签），前端展示用 |
| `description_text` | TEXT | YES | NULL | — | JD 纯文本（爬虫层 HTML→Text），**喂给 ES/向量化/星火** |
| `highlights` | JSON | YES | NULL | — | 岗位亮点标签（如 `["弹性工作","股票期权"]`） |
| `advantage` | TEXT | YES | NULL | — | 岗位亮点文案 |
| `work_address` | VARCHAR(255) | YES | NULL | — | 详细工作地址 |
| `longitude` | DECIMAL(10,7) | YES | NULL | — | 经度（用于地理搜索） |
| `latitude` | DECIMAL(10,7) | YES | NULL | — | 纬度 |
| `source` | VARCHAR(32) | NO | 'boss' | **UNI**（联合） | 数据来源 |
| `source_url` | VARCHAR(512) | NO | — | — | 原始 URL，**用户点击跳转用** |
| `source_id` | VARCHAR(64) | YES | NULL | **UNI**（联合） | 平台原始 ID，**爬虫去重核心** |
| `crawl_batch` | VARCHAR(32) | YES | NULL | — | 采集批次号（如 `20260613_BOSS_PY_001`），便于回滚 |
| `status` | VARCHAR(16) | NO | 'active' | MUL | 状态：`active`（招聘中）/ `closed`（关闭）/ `expired`（过期） |
| `publish_at` | DATETIME | YES | NULL | MUL | 平台发布时间 |
| `crawl_at` | DATETIME | YES | NULL | — | 爬虫抓取时间 |
| `quality_score` | DECIMAL(4,2) | YES | NULL | — | 数据质量评分（0-100），低分不入推荐池 |
| `is_deleted` | TINYINT(1) | NO | 0 | — | 软删除 |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间 |

**索引说明**：
- `uk_job_code`：对外编码唯一
- `uk_job_source`：(source, source_id) 联合唯一，**跨平台爬虫去重**
- `idx_job_company`：按公司查询职位
- `idx_job_city`：按城市筛选
- `idx_job_status`：只看 `active` 职位
- `idx_job_publish`：按发布时间排序（"最新发布"）
- `idx_job_salary`：薪资范围筛选

**为什么 `description` 和 `description_text` 都存？**
- `description` 含 HTML，前端直接渲染
- `description_text` 纯文本，避免每次检索都清洗 HTML，性能更好

**薪资设计的三字段策略**：
- `salary_min` / `salary_max`：范围查询
- `salary_unit`：应对实习（日薪）、外包（年薪）的差异性
- `salary_months`：13/14 薪影响实际年薪

---

### 2.8 `job_skills` 职位技能关联

**用途**：职位与技能的多对多关联，匹配算法核心。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `job_id` | BIGINT UNSIGNED | NO | — | MUL | 职位 ID |
| `skill_id` | BIGINT UNSIGNED | NO | — | MUL | 技能 ID |
| `is_must` | TINYINT(1) | NO | 0 | — | **是否必须技能**（1=必须，缺失直接淘汰） |
| `weight` | DECIMAL(4,2) | YES | 1.00 | — | 权重，影响匹配评分 |

**索引说明**：
- `uk_job_skill`：(job_id, skill_id) 联合唯一
- `idx_js_skill`：反向查询"某技能被多少职位需要"

**匹配逻辑**：
- `is_must=1` 的技能缺失 → 直接过滤该职位
- `is_must=0` 的技能匹配 → 加分但不过滤

---

## 三、行为层

行为层记录用户在系统中的所有操作和系统输出（投递、推荐、对话）。

### 3.1 `applications` 用户-职位关系

**用途**：用户对职位的所有交互行为。**本平台不代投**，只提供 `jobs.source_url` 让用户跳转到外站投递，因此 `submitted` 之后的状态完全依赖用户回站手动反馈。

**产品定位**：信息聚合 + 推荐 + 跳转中转站。此表实际承担"用户求职进度看板"角色，而非投递日志。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `user_id` | BIGINT UNSIGNED | NO | — | MUL | 用户 ID |
| `job_id` | BIGINT UNSIGNED | NO | — | MUL | 职位 ID |
| `resume_id` | BIGINT UNSIGNED | YES | NULL | — | 跳转时参考的简历（用户对比推荐分时使用） |
| `status` | VARCHAR(16) | NO | 'clicked' | — | 状态机：`clicked` / `favorited` / `submitted` / `interviewed` / `offer` / `rejected` |
| `match_score` | DECIMAL(5,2) | YES | NULL | — | 推荐时的匹配分（0-100），用于效果分析 |
| `redirected_at` | DATETIME | YES | NULL | — | 点击跳转到外站的时间（平台可自动记录） |
| `submitted_at` | DATETIME | YES | NULL | — | 用户反馈已在外站投递的时间 |
| `feedback_at` | DATETIME | YES | NULL | — | 用户最近一次手动反馈时间（催回访用） |
| `click_count` | INT UNSIGNED | NO | 0 | — | 跳转点击次数，用于职位热度/重复访问统计 |
| `external_source` | VARCHAR(32) | YES | NULL | — | 用户实际投递来源 `boss` / `liepin` / `official` |
| `note` | VARCHAR(512) | YES | NULL | — | 用户备注（面试进度、HR 联系方式、薪资沟通等） |
| `is_deleted` | TINYINT(1) | NO | 0 | — | 软删除 |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间 |

**索引说明**：
- `uk_user_job`：(user_id, job_id) 联合唯一，**同一用户对同一职位只一条记录**，状态机演进
- `idx_app_user_status`：(user_id, status) 复合索引，覆盖"我的收藏""我的投递反馈"高频查询
- `idx_app_job`：反向查询"某职位被多少人点击/投递"，用于热度排序

**状态机演进示例**：
```
clicked → favorited → submitted → interviewed → offer
         (自动)        (用户反馈)    (用户反馈)    (用户反馈)
                                            ↘ rejected (用户反馈)
```

**平台可自动感知 vs 用户手动反馈**：

| 状态 | 自动感知 | 说明 |
|---|---|---|
| `clicked` | ✅ | 用户点击"去投递"按钮跳转时自动记录 |
| `favorited` | ✅ | 平台内收藏动作 |
| `submitted` | ❌ | 用户回站手动标记"已在外站投递" |
| `interviewed` | ❌ | 用户反馈进入面试 |
| `offer` / `rejected` | ❌ | 用户反馈最终结果 |

**核心 UX 设计**：定期引导用户回访"上次跳转的 XX 公司职位，投递结果如何？"，是提升此表数据完整性的关键。

**与 `recommendations` 的关系**：推荐效果闭环 = `recommendations.score`（系统视角）↔ `applications.clicked/submitted`（用户视角）。

---

### 3.2 `recommendations` 推荐流水

**用途**：每次推荐生成的记录，用于 A/B 测试、效果回溯、推荐理由展示。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `user_id` | BIGINT UNSIGNED | NO | — | MUL | 用户 ID |
| `resume_id` | BIGINT UNSIGNED | YES | NULL | — | 简历 ID（冷启动可能没有简历） |
| `job_id` | BIGINT UNSIGNED | NO | — | — | 推荐的职位 ID |
| `score` | DECIMAL(5,2) | NO | — | — | 匹配评分（0-100） |
| `reason` | TEXT | YES | NULL | — | **推荐理由**（LLM 生成，回显给用户增加信任） |
| `strategy` | VARCHAR(32) | NO | 'rag' | MUL | 推荐策略：`rag` / `graph` / `hybrid` / `cold_start` |
| `snapshot` | JSON | YES | NULL | — | **推荐时特征快照**（技能向量、地理位置等） |
| `clicked` | TINYINT(1) | NO | 0 | — | 用户是否点击（0=未点击，1=已点击） |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 推荐时间 |

**索引说明**：
- `idx_rec_user`：(user_id, created_at) 复合索引，按用户查推荐历史
- `idx_rec_strategy`：按策略分组（A/B 测试效果对比）

**`snapshot` JSON 字段的妙用**：
用户一个月后改了简历，历史推荐评分需要当时的特征 —— 快照解决时间一致性问题。

---

### 3.3 `chat_history` AI 对话历史

**用途**：用户与 AI 助手的对话记录，用于上下文管理和计费。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `user_id` | BIGINT UNSIGNED | NO | — | MUL | 用户 ID |
| `session_id` | VARCHAR(64) | NO | — | MUL | 会话 ID，**多轮对话上下文隔离** |
| `role` | VARCHAR(16) | NO | — | — | 消息角色：`user`（用户）/ `assistant`（AI）/ `system`（系统提示词） |
| `content` | MEDIUMTEXT | NO | — | — | 消息内容 |
| `tool_calls` | JSON | YES | NULL | — | LLM 工具调用记录（查询了哪些职位、调用了哪些函数） |
| `tokens` | INT | YES | NULL | — | 消耗 token 数，**计费和限流用** |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |

**索引说明**：
- `idx_chat_session`：(session_id, created_at) 复合索引，加载会话历史
- `idx_chat_user`：按用户查询所有对话

---

## 四、采集层

采集层管理爬虫的数据源和任务执行，让爬虫运维可观测、可重试。

### 4.1 `crawl_sources` 数据源配置

**用途**：爬虫数据源配置表，**换页面结构时只改 DB 不改代码**。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | INT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `name` | VARCHAR(64) | NO | — | **UNI**（联合） | 数据源名称（如 `boss` / `liepin` / `qcc`） |
| `type` | VARCHAR(32) | NO | 'job' | **UNI**（联合） | 数据类型：`job`（职位）/ `company`（公司） |
| `base_url` | VARCHAR(255) | YES | NULL | — | 基础 URL |
| `enabled` | TINYINT(1) | NO | 1 | — | 是否启用（0=禁用，1=启用） |
| `config` | JSON | YES | NULL | — | 抓取规则配置（选择器、反爬策略、限流参数） |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |

**索引说明**：
- `uk_source_name`：(name, type) 联合唯一

**`config` JSON 示例**：
```json
{
  "list_selector": ".job-list li",
  "title_selector": ".job-title",
  "rate_limit": {"qps": 1, "burst": 5},
  "proxy_pool": "enabled"
}
```

---

### 4.2 `crawl_tasks` 爬虫任务记录

**用途**：爬虫任务执行流水，用于失败重试、效果统计、批次追溯。

| 字段 | 类型 | 可空 | 默认值 | 键 | 说明 |
|---|---|---|---|---|---|
| `id` | BIGINT UNSIGNED | NO | AUTO_INCREMENT | **PRI** | 自增主键 |
| `source_id` | INT UNSIGNED | NO | — | MUL | 数据源 ID |
| `task_code` | VARCHAR(64) | NO | — | **UNI** | 任务编码 |
| `keyword` | VARCHAR(128) | YES | NULL | — | 搜索关键词（如 `Python`） |
| `city` | VARCHAR(64) | YES | NULL | — | 目标城市 |
| `status` | VARCHAR(16) | NO | 'pending' | MUL | 状态：`pending` / `running` / `success` / `failed` |
| `total` | INT | YES | 0 | — | 预期抓取数量 |
| `succeeded` | INT | YES | 0 | — | 成功数量 |
| `failed` | INT | YES | 0 | — | 失败数量 |
| `error_msg` | VARCHAR(512) | YES | NULL | — | 失败原因 |
| `start_at` | DATETIME | YES | NULL | — | 实际开始时间 |
| `end_at` | DATETIME | YES | NULL | — | 实际结束时间 |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — | 创建时间 |

**索引说明**：
- `uk_task_code`：任务编码唯一
- `idx_task_status`：按状态筛选（如查所有 `failed` 任务进行重试）
- `idx_task_source`：按数据源统计任务

---

## 五、通用约定

### 5.1 字段命名规范

| 规范 | 示例 |
|---|---|
| 主键统一 `id` (BIGINT UNSIGNED AUTO_INCREMENT) | `id` |
| 对外编码 `*_code` (VARCHAR(64)) | `user_code`, `job_code` |
| 时间字段 `*_at` (DATETIME) | `created_at`, `publish_at` |
| 软删除 `is_deleted` (TINYINT(1)) | 默认 0 |
| 来源标记 `source` (VARCHAR(32)) | `boss`, `liepin`, `official` |
| 外键 `*_id` (BIGINT UNSIGNED) | `user_id`, `job_id` |

### 5.2 状态机汇总

| 表 | 字段 | 状态流转 |
|---|---|---|
| `resumes` | `parse_status` | pending → parsing → done / failed |
| `jobs` | `status` | active → closed / expired |
| `applications` | `status` | clicked → favorited → submitted → interviewed → offer / rejected（submitted 后状态依赖用户手动反馈） |
| `crawl_tasks` | `status` | pending → running → success / failed |

### 5.3 软删除约定

所有业务表带 `is_deleted`：
- **不物理删除**：保留数据用于审计、回滚
- **查询时过滤**：`WHERE is_deleted = 0`
- **定期归档**：超过 1 年的软删除数据迁移到 `*_archive` 表

### 5.4 索引设计原则

```
原则1: 唯一索引优先 → uk_* 解决去重 + 查询二合一
原则2: 复合索引左前缀 → (user_id, status) 覆盖高频
原则3: 软删除不下索引 → 区分率低（90% 是 0），索引反而拖慢写入
原则4: 长文本不下索引 → 走 ES 全文检索
```

### 5.5 字符集

- 数据库默认：`utf8mb4` / `utf8mb4_unicode_ci`
- **必须 utf8mb4**（非 utf8），支持 emoji 和生僻字
- 校对集 `unicode_ci` 支持不区分大小写比较

---

## 六、ER 关系图

```
                    ┌──────────┐
                    │  users   │
                    └────┬─────┘
                         │1:N
              ┌──────────┼──────────────┐
              ▼          ▼              ▼
        ┌──────────┐ ┌────────────┐  ┌──────────────────┐
        │ resumes  │ │applications│  │ recommendations  │
        └────┬─────┘ └─────┬──────┘  └────────┬─────────┘
             │1:N           │                  │
    ┌────────┼────────┐     │                  │
    ▼        ▼        ▼     │                  │
┌────────┐┌──────┐┌─────┐  │                  │
│  exp   ││ edu  ││rsm  │  │                  │
│        ││      ││skl  │  │                  │
└────────┘└──────┘└──┬──┘  │                  │
                    │ M:N │                  │
                    ▼     ▼                  │
                 ┌──────────┐                │
                 │  skills  │                │
                 └────┬─────┘                │
                      │ M:N                  │
                      ▼                      │
                 ┌────────────┐              │
                 │ job_skills │              │
                 └─────┬──────┘              │
                       │ N:1                 │
                       ▼                     │
                 ┌──────────┐    N:1    ┌────┴─────┐
                 │   jobs   │◄──────────│applications│
                 └────┬─────┘           └──────────┘
                      │ N:1
                      ▼
                 ┌───────────┐
                 │ companies │
                 └───────────┘

字典层:  skills ←→ industries
采集层:  crawl_sources ──1:N──> crawl_tasks
对话:    users ──1:N──> chat_history
```

**关系说明**：
- `users` 1:N `resumes`（一个用户多份简历）
- `resumes` 1:N `resume_experiences` / `resume_educations`（一份简历多段经历）
- `resumes` N:M `skills`（通过 `resume_skills`）
- `companies` 1:N `jobs`（一个公司多个职位）
- `jobs` N:M `skills`（通过 `job_skills`）
- `users` N:M `jobs`（通过 `applications`）
- `users` 1:N `recommendations`（推荐流水）
- `users` 1:N `chat_history`（对话历史）

---

## 附：表清单速查

| 序号 | 表名 | 层级 | 说明 | 关键记录数（种子） |
|---|---|---|---|---|
| 1 | `skills` | 字典层 | 技能标准化字典 | 25 |
| 2 | `industries` | 字典层 | 行业层级字典 | 8 |
| 3 | `users` | 主体层 | 系统用户 | 2 |
| 4 | `resumes` | 主体层 | 简历主表 | 0 |
| 5 | `resume_skills` | 主体层 | 简历-技能关联 | 0 |
| 6 | `resume_experiences` | 主体层 | 工作经历 | 0 |
| 7 | `resume_educations` | 主体层 | 教育经历 | 0 |
| 8 | `companies` | 主体层 | 公司信息 | 0 |
| 9 | `jobs` | 主体层 | 职位主表 | 0 |
| 10 | `job_skills` | 主体层 | 职位-技能关联 | 0 |
| 11 | `applications` | 行为层 | 用户-职位关系 | 0 |
| 12 | `recommendations` | 行为层 | 推荐流水 | 0 |
| 13 | `chat_history` | 行为层 | AI 对话历史 | 0 |
| 14 | `crawl_sources` | 采集层 | 爬虫数据源配置 | 0 |
| 15 | `crawl_tasks` | 采集层 | 爬虫任务记录 | 0 |

---

**文档版本**：v1.0
**对应 SQL 文件**：`backend/db/mysql/01_schema.sql`、`02_seed.sql`
**维护建议**：每次 schema 变更需同步更新此文档，保持单一真相源。
