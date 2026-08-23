# JobHunter Elasticsearch 索引字段说明文档

> **Elasticsearch 版本**：9.4.2
> **已安装插件**：`analysis-ik 9.4.2`（IK 中文分词器）
> **共 3 个业务索引**：`jobs` / `resumes` / `companies`
> **生成时间**：2026-06-13

---

## 目录

- [一、ES 在系统中的角色](#一es-在系统中的角色)
- [二、分词器与分析器](#二分词器与分析器)
- [三、索引详解](#三索引详解)
  - [3.1 `jobs` 职位索引](#31-jobs-职位索引)
  - [3.2 `resumes` 简历索引](#32-resumes-简历索引)
  - [3.3 `companies` 公司索引](#33-companies-公司索引)
- [四、字段类型设计哲学](#四字段类型设计哲学)
- [五、典型查询场景](#五典型查询场景)
- [六、与 MySQL 的同步策略](#六与-mysql-的同步策略)
- [七、索引运维](#七索引运维)

---

## 一、ES 在系统中的角色

```
┌─────────────────────────────────────────────────────────────────┐
│  存储分工                                                       │
├─────────────────────────────────────────────────────────────────┤
│  MySQL (真相源)   →  事务、强一致、关联查询                     │
│  Elasticsearch    →  全文检索、聚合分析、模糊匹配、地理搜索     │
│  Neo4j            →  关系图、多跳路径、社区发现                 │
│  ChromaDB         →  向量检索（RAG 语义召回）                   │
└─────────────────────────────────────────────────────────────────┘
```

**核心定位**：ES 是 MySQL 的「查询加速副本」，不存储真相数据。所有业务写入只走 MySQL，由同步服务异步推送到 ES。

**为什么需要 ES**：
| 场景 | MySQL 表现 | ES 表现 |
|---|---|---|
| "Python + 上海 + 15-25K" 多条件模糊搜 | LIKE 慢，无法分词 | ✅ IK 分词 + 多 filter，毫秒级 |
| "最近 30 天 Python 工程师薪资分布" 聚合 | GROUP BY 全表扫描 | ✅ bucket 聚合，亚秒级 |
| 搜索框输入"py"自动补全 | 每次 LIKE 全表 | ✅ completion 类型，10ms 内 |
| "公司 5km 内的职位" 地理搜索 | 不支持 | ✅ geo_point + geo_distance |
| "React 开发"也能搜到"前端工程师" | 关键词不匹配 | ✅ 分词后召回 |

---

## 二、分词器与分析器

### 2.1 已配置的自定义分析器

| 分析器名 | 类型 | 用途 |
|---|---|---|
| `ik_smart_analyzer` | custom | **搜索时使用**（用户输入），分词粗粒度，提高召回率 |
| `ik_max_analyzer` | custom | **索引时使用**（写入文档），分词细粒度，提高查全率 |

### 2.2 配置详情

```json
{
  "analysis": {
    "analyzer": {
      "ik_smart_analyzer": {
        "type": "custom",
        "tokenizer": "ik_smart",
        "filter": ["lowercase", "asciifolding"]
      },
      "ik_max_analyzer": {
        "type": "custom",
        "tokenizer": "ik_max_word",
        "filter": ["lowercase", "asciifolding"]
      }
    }
  }
}
```

### 2.3 filter 作用

| Filter | 作用 | 示例 |
|---|---|---|
| `lowercase` | 转小写 | `Python` → `python`，避免大小写敏感 |
| `asciifolding` | ASCII 折叠 | `café` → `cafe`，处理外来字符 |

### 2.4 IK 分词器对比

**索引时用 `ik_max_word`（最细粒度）**：
```
输入: "Python 高级工程师"
分词: ["Python", "高级", "工程师", "工程", "师"]
```
**搜索时用 `ik_smart`（智能切分）**：
```
输入: "Python 高级工程师"
分词: ["Python", "高级工程师"]
```

**为什么这样配？** 索引时多切分一些词，确保任何搜索词都能命中；搜索时少切分，避免召回过多无关结果。

---

## 三、索引详解

### 3.1 `jobs` 职位索引

**用途**：职位全文检索、多条件筛选、地理搜索、自动补全。

#### Settings

| 配置项 | 值 | 说明 |
|---|---|---|
| `number_of_shards` | 1 | 分片数（单机部署，生产环境按数据量调整） |
| `number_of_replicas` | 0 | 副本数（开发环境 0，生产至少 1） |

#### Mapping 字段表

| 字段 | 类型 | 分析器 | 子字段 | 说明 |
|---|---|---|---|---|
| `job_id` | long | — | — | MySQL 中 `jobs.id`，反向同步用 |
| `job_code` | keyword | — | — | 对外编码，精确匹配 |
| `title` | text | ik_max_analyzer | `keyword` / `suggest` | 职位标题 |
| `title.keyword` | keyword | — | — | 用于聚合、排序 |
| `title.suggest` | completion | ik_max_analyzer | — | **搜索框自动补全** |
| `description_text` | text | ik_max_analyzer | — | JD 纯文本，全文检索主战场 |
| `company_id` | long | — | — | 公司 ID（MySQL 关联） |
| `company_name` | text | ik_max_analyzer | `keyword` | 公司名称（冗余存储避免 join） |
| `company_size` | keyword | — | — | 公司规模 |
| `company_stage` | keyword | — | — | 融资阶段 |
| `city` | keyword | — | — | 城市 |
| `district` | keyword | — | — | 区县 |
| `salary_min` | integer | — | — | 薪资下限（元/月） |
| `salary_max` | integer | — | — | 薪资上限 |
| `salary_months` | short | — | — | 几薪（13/14） |
| `experience_req` | keyword | — | — | 经验要求 |
| `education_req` | keyword | — | — | 学历要求 |
| `job_type` | keyword | — | — | 职位类型 |
| `skills` | keyword | — | — | 技能 ID 数组（精确过滤+聚合） |
| `skills_text` | text | ik_max_analyzer | — | 技能名拼接（模糊召回） |
| `highlights` | keyword | — | — | 岗位亮点标签 |
| `welfare` | keyword | — | — | 公司福利标签 |
| `industry_code` | keyword | — | — | 行业编码 |
| `publish_at` | date | — | — | 发布时间 |
| `crawl_at` | date | — | — | 抓取时间 |
| `created_at` | date | — | — | 入库时间 |
| `status` | keyword | — | — | 职位状态 |
| `source` | keyword | — | — | 数据来源 |
| `source_url` | keyword | — | — | 原始 URL，**index=false 不索引** |
| `quality_score` | float | — | — | 质量评分 |
| `location` | geo_point | — | — | **地理位置（经纬度）** |

#### 关键设计点

**1. `title` 的三重字段设计**
```
title:           text     → 全文搜索主战场
title.keyword:   keyword  → 聚合统计（如"按职位名分组"）
title.suggest:   completion → 搜索框自动补全
```

**2. `skills` vs `skills_text` 双字段**
```
skills:        keyword → 精确过滤"必须含 Python 技能"
skills_text:   text    → 模糊召回"会 Spring 也算 Java 方向"
```
**为什么双字段？** keyword 用于硬过滤（match），text 用于软召回（should），互补。

**3. `source_url` 关闭索引**
```json
"source_url": { "type": "keyword", "index": false, "doc_values": false }
```
**为什么？** 没人会按 URL 搜索，关闭索引和 doc_values 节省 30% 索引空间。

**4. `location` 地理搜索**
支持「公司 5km 内的 Python 职位」这类查询：
```json
{
  "geo_distance": {
    "distance": "5km",
    "location": { "lat": 31.2304, "lon": 121.4737 }
  }
}
```

**5. 日期字段统一 format**
```json
"format": "strict_date_optional_time||epoch_millis"
```
同时支持 `2026-06-13`、`2026-06-13T10:30:00Z`、毫秒时间戳三种格式。

---

### 3.2 `resumes` 简历索引

**用途**：相似简历召回、候选人反向搜索（HR 视角）。

#### Settings

与 `jobs` 索引一致（ik_smart + ik_max 双分析器）。

#### Mapping 字段表

| 字段 | 类型 | 分析器 | 子字段 | 说明 |
|---|---|---|---|---|
| `resume_id` | long | — | — | MySQL 中 `resumes.id` |
| `resume_code` | keyword | — | — | 对外编码 |
| `user_id` | long | — | — | 用户 ID |
| `name` | keyword | — | — | 姓名（精确匹配，不索引中文） |
| `expect_job` | text | ik_max_analyzer | — | 期望岗位，全文检索 |
| `city` | keyword | — | — | 现居城市 |
| `expect_city` | keyword | — | — | 期望城市 |
| `work_years` | integer | — | — | 工作年限（范围查询） |
| `education` | keyword | — | — | 最高学历 |
| `expect_salary_min` | integer | — | — | 期望薪资下限 |
| `expect_salary_max` | integer | — | — | 期望薪资上限 |
| `skills` | keyword | — | — | 技能 ID 数组 |
| `skills_text` | text | ik_max_analyzer | — | 技能名拼接 |
| `experience_summary` | text | ik_max_analyzer | — | 工作经历摘要（NER 抽取后生成） |
| `companies` | keyword | — | — | 曾任职公司列表 |
| `schools` | keyword | — | — | 毕业院校列表 |
| `overall_score` | float | — | — | 简历完整度评分 |
| `updated_at` | date | — | — | 更新时间 |

#### 关键设计点

**1. `name` 为什么是 keyword 不是 text？**
中文姓名不需要分词（"张三"分成"张"和"三"无意义），用 keyword 做精确匹配。

**2. `experience_summary` 的作用**
工作经历原文太长不适合直接索引，由 NER 抽取后生成 100 字内的摘要：
```
"在阿里巴巴担任高级Java工程师3年，负责交易系统开发，
技术栈包括 Spring Cloud、MySQL、Redis..."
```

**3. `companies` / `schools` 数组字段**
ES 天然支持数组，无需特殊声明：
```json
"companies": ["阿里巴巴", "腾讯", "字节跳动"],
"schools": ["浙江大学", "复旦大学"]
```

**4. `skills` + `skills_text` 双字段**（同 jobs）
支持「必须有 Python 技能」硬过滤 + 「会 Java 方向」软召回。

---

### 3.3 `companies` 公司索引

**用途**：公司搜索、自动补全、按行业/规模聚合分析。

#### Settings

与 `jobs` 索引一致。

#### Mapping 字段表

| 字段 | 类型 | 分析器 | 子字段 | 说明 |
|---|---|---|---|---|
| `company_id` | long | — | — | MySQL 中 `companies.id` |
| `company_code` | keyword | — | — | 对外编码 |
| `name` | text | ik_max_analyzer | `keyword` / `suggest` | 公司名 |
| `name.keyword` | keyword | — | — | 用于聚合排序 |
| `name.suggest` | completion | ik_max_analyzer | — | 搜索框自动补全 |
| `short_name` | keyword | — | — | 公司简称 |
| `industry_code` | keyword | — | — | 行业编码 |
| `size` | keyword | — | — | 公司规模 |
| `stage` | keyword | — | — | 融资阶段 |
| `city` | keyword | — | — | 城市 |
| `district` | keyword | — | — | 区县 |
| `welfare` | keyword | — | — | 福利标签 |
| `description` | text | ik_max_analyzer | — | 公司介绍 |
| `job_count` | integer | — | — | **在招职位数**（冗余字段） |
| `created_at` | date | — | — | 创建时间 |

#### 关键设计点

**1. `job_count` 冗余字段**
直接存储"该公司当前在招职位数"，避免每次搜索都 join jobs 索引统计。
- MySQL jobs 表变更时，同步更新对应 company 的 `job_count`
- 排序场景：「在招职位最多的公司」直接按 `job_count` desc

**2. `name.suggest` 自动补全**
用户输入"阿"自动补全"阿里巴巴集团"：
```json
POST /companies/_search
{
  "suggest": {
    "company-suggest": {
      "prefix": "阿",
      "completion": { "field": "name.suggest", "size": 10 }
    }
  }
}
```

**3. `description` 全文检索**
支持「有员工食堂的公司」「弹性工作制的公司」这类自然语言搜索。

---

## 四、字段类型设计哲学

### 4.1 类型选择决策树

```
字段值是日期？
  └─ Yes → date
字段值是数字？
  └─ Yes → 是否需要范围查询？
            ├─ Yes → integer/long/float
            └─ No  → keyword（如手机号、ID）
字段值是布尔？
  └─ Yes → 用 keyword ("true"/"false")，避免 boolean 的存储浪费
字段值是固定枚举？
  └─ Yes → keyword（精确匹配 + 聚合）
字段值是短文本（如标签）？
  └─ Yes → keyword
字段值是长文本（如描述）？
  └─ Yes → text
            ├─ 需要聚合/排序？ → 加 .keyword 子字段
            └─ 需要自动补全？ → 加 .suggest 子字段(completion)
字段值是经纬度？
  └─ Yes → geo_point
字段值是数组？
  └─ ES 天然支持，类型照常声明
```

### 4.2 keyword vs text 对比

| 维度 | keyword | text |
|---|---|---|
| 是否分词 | ❌ 整体作为一个 token | ✅ 经过分析器切分 |
| 精确匹配 | ✅ term 查询高效 | ❌ 需要 .keyword 子字段 |
| 全文搜索 | ❌ | ✅ |
| 聚合/排序 | ✅ | ❌（需 .keyword） |
| 适用场景 | ID、枚举、标签、URL | 标题、描述、内容 |

### 4.3 多字段（multi-field）策略

对于"既要又要"的字段，用 `.keyword` / `.suggest` 子字段：

```json
"title": {
  "type": "text",
  "analyzer": "ik_max_analyzer",
  "fields": {
    "keyword": { "type": "keyword" },        // 聚合用
    "suggest": { "type": "completion" }       // 补全用
  }
}
```

**使用场景**：
- 全文搜索 → `match { "title": "Python" }`
- 精确匹配/聚合 → `term { "title.keyword": "高级Python工程师" }`
- 自动补全 → `suggest { "completion": { "field": "title.suggest" } }`

---

## 五、典型查询场景

### 5.1 多条件职位搜索

**场景**：找"上海，月薪 15-25K，需要 Python 技能"的职位

```json
POST /jobs/_search
{
  "query": {
    "bool": {
      "must": [
        { "term": { "city": "上海" } },
        { "term": { "status": "active" } },
        { "range": { "salary_min": { "lte": 25000 } } },
        { "range": { "salary_max": { "gte": 15000 } } },
        { "match": { "skills_text": "Python" } }
      ],
      "should": [
        { "match": { "description_text": "FastAPI" } }
      ]
    }
  },
  "sort": [
    { "publish_at": { "order": "desc" } },
    { "_score": { "order": "desc" } }
  ]
}
```

### 5.2 搜索框自动补全

```json
POST /jobs/_search
{
  "suggest": {
    "job-suggest": {
      "prefix": "py",
      "completion": { "field": "title.suggest", "size": 10, "skip_duplicates": true }
    }
  }
}
```

### 5.3 地理范围搜索

**场景**：找杭州西湖区 5km 内的 Java 职位

```json
POST /jobs/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "title": "Java" } },
        {
          "geo_distance": {
            "distance": "5km",
            "location": { "lat": 30.2592, "lon": 120.1300 },
            "distance_type": "arc"
          }
        }
      ]
    }
  },
  "sort": [
    {
      "_geo_distance": {
        "location": { "lat": 30.2592, "lon": 120.1300 },
        "order": "asc",
        "unit": "km"
      }
    }
  ]
}
```

### 5.4 聚合分析

**场景**：统计上海 Python 职位的薪资分布

```json
POST /jobs/_search
{
  "size": 0,
  "query": { "term": { "city": "上海" } },
  "aggs": {
    "salary_ranges": {
      "range": {
        "field": "salary_max",
        "ranges": [
          { "to": 10000 },
          { "from": 10000, "to": 20000 },
          { "from": 20000, "to": 30000 },
          { "from": 30000, "to": 50000 },
          { "from": 50000 }
        ]
      },
      "aggs": {
        "avg_min": { "avg": { "field": "salary_min" } }
      }
    },
    "top_skills": {
      "terms": { "field": "skills", "size": 10 }
    }
  }
}
```

### 5.5 相似简历召回

**场景**：找与简历 A 相似的候选人（技能重叠度高）

```json
POST /resumes/_search
{
  "query": {
    "more_like_this": {
      "fields": ["skills_text", "experience_summary"],
      "like": [
        { "_index": "resumes", "_id": "1" }
      ],
      "min_term_freq": 1,
      "min_doc_freq": 1
    }
  }
}
```

---

## 六、与 MySQL 的同步策略

### 6.1 同步方向

```
MySQL (真相源)
   │
   ├──> Elasticsearch (异步, 容忍秒级延迟)
   │    触发: jobs/companies/resumes 表 INSERT/UPDATE
   │
   ├──> Neo4j (异步, 由 NER 触发)
   │
   └──> ChromaDB (异步, 由向量化任务触发)
```

### 6.2 推荐方案：应用层双写 + Outbox 模式

```
1. 业务代码写入 MySQL
2. 同时写一条 outbox 事件 (status=pending)
3. 后台 worker 轮询 outbox, 推送 ES
4. 推送成功后 outbox.status=done
5. 失败重试 3 次, 进死信队列
```

**优势**：
- 不依赖 binlog（Canal 部署复杂）
- 业务可控，可定制转换逻辑
- 失败可重试，最终一致

### 6.3 字段映射表（MySQL → ES）

#### jobs 表

| MySQL 字段 | ES 字段 | 转换说明 |
|---|---|---|
| `id` | `job_id` | 直接映射 |
| `job_code` | `job_code` | 直接映射 |
| `title` | `title` / `title.suggest` | completion 需特别处理 |
| `description_text` | `description_text` | 直接映射 |
| `company_id` | `company_id` | 直接映射 |
| （join companies） | `company_name` / `company_size` / `company_stage` | **冗余查询**，避免 ES join |
| `city` / `district` | `city` / `district` | 直接映射 |
| `salary_min` / `salary_max` / `salary_months` | 同名 | 直接映射 |
| `experience_req` / `education_req` / `job_type` | 同名 | 直接映射 |
| （join job_skills） | `skills` / `skills_text` | skills 是 ID 数组，skills_text 是名称拼接 |
| `highlights` / `welfare` | 同名 | JSON → 数组 |
| `industry_code` | 同名 | join companies 取 |
| `publish_at` / `crawl_at` / `created_at` | 同名 | 直接映射 |
| `status` / `source` | 同名 | 直接映射 |
| `source_url` | 同名 | 直接映射（index=false） |
| `quality_score` | 同名 | 直接映射 |
| `longitude` + `latitude` | `location` | **合并为 geo_point** |

### 6.4 软删除处理

MySQL 中 `is_deleted=1` 的记录，**ES 中直接删除文档**：
```python
if record.is_deleted:
    es.delete(index="jobs", id=record.id)
else:
    es.index(index="jobs", id=record.id, document=es_doc)
```

---

## 七、索引运维

### 7.1 别名（Alias）策略

**生产推荐**：索引用版本号，通过别名对外暴露，实现零停机重建。

```
jobs_v1 (实际索引)
   ↑
jobs (别名)  ← 应用代码使用
```

**重建流程**：
```
1. 创建 jobs_v2 (新 mapping)
2. reindex jobs_v1 → jobs_v2
3. 切换别名 jobs → jobs_v2
4. 删除 jobs_v1
```

### 7.2 监控指标

| 指标 | 告警阈值 | 检查命令 |
|---|---|---|
| 集群健康状态 | `yellow` 警告 / `red` 严重 | `GET /_cluster/health` |
| 索引文档数突降 | 1 小时内降 >10% | `GET /_cat/indices` |
| 查询延迟 | P99 > 500ms | `GET /_nodes/stats/indices/search` |
| 磁盘使用率 | >80% 警告 | `GET /_cat/allocation?v` |

### 7.3 性能优化要点

**1. 分片设置**
- 单分片建议 < 50GB
- 分片数 = 数据量 / 50GB（向上取整）
- 副本数：开发 0，生产 ≥1

**2. Refresh interval**
默认 1 秒 refresh，批量写入时临时调大：
```json
PUT /jobs/_settings
{ "refresh_interval": "30s" }
```
批量完成后再调回 `"1s"`。

**3. 批量写入**
用 `_bulk` API，单批次 5-15MB 最佳：
```json
POST /_bulk
{ "index": { "_index": "jobs", "_id": "1" } }
{ "job_id": 1, "title": "Python工程师", ... }
{ "index": { "_index": "jobs", "_id": "2" } }
{ "job_id": 2, "title": "Java工程师", ... }
```

**4. 关闭不需要索引的字段**
如 `source_url` 设 `index: false` + `doc_values: false`，节省 30% 空间。

### 7.4 灾备

- **快照备份**：每日 snapshot 到本地/NAS
- **跨集群复制（CCR）**：生产环境跨机房灾备

---

## 附：索引清单速查

| 序号 | 索引名 | 用途 | 文档数 | 关键特性 |
|---|---|---|---|---|
| 1 | `jobs` | 职位检索 | 0 | IK 分词、geo_point、completion |
| 2 | `resumes` | 简历检索 | 0 | IK 分词、相似召回 |
| 3 | `companies` | 公司检索 | 0 | completion 自动补全 |

---

## 附：字段类型速查

| 类型 | 用途 | 索引中字段示例 |
|---|---|---|
| `long` | 大整数 ID | `job_id`, `company_id`, `user_id` |
| `integer` | 范围数字 | `salary_min`, `work_years`, `job_count` |
| `short` | 小整数 | `salary_months` |
| `float` | 评分 | `quality_score`, `overall_score` |
| `keyword` | 精确匹配/聚合 | `city`, `status`, `skills` |
| `text` | 全文检索 | `title`, `description_text` |
| `text` + `.keyword` | 双用途 | `company_name` |
| `text` + `.suggest` | 补全 | `title`, `name` |
| `date` | 时间 | `publish_at`, `created_at` |
| `geo_point` | 地理位置 | `location` |
| `completion` | 自动补全 | `title.suggest`, `name.suggest` |

---

**文档版本**：v1.0
**对应 JSON 文件**：
- `backend/db/es/jobs_index.json`
- `backend/db/es/resumes_index.json`
- `backend/db/es/companies_index.json`

**维护建议**：
- 索引 mapping 变更需同步更新此文档
- 新增字段时参考「字段类型设计哲学」决策树
- 生产环境重建索引走「别名策略」流程
