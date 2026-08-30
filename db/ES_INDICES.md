# JobHunter Elasticsearch 索引说明文档

> **Elasticsearch 版本**：9.4.2（本地安装于 `C:\RJ\elasticsearch-9.4.2`）
> **分词插件**：`analysis-ik`（IK 中文分词器）
> **实际索引**：`jobs`（1 个，本文档以此为准）
> **更新时间**：2026-08-30

---

## 一、ES 在系统中的角色

```
┌──────────────────────────────────────────────────────────┐
│  存储分工(实际实现)                                       │
├──────────────────────────────────────────────────────────┤
│  MySQL (真相源)   → 事务、强一致、关联查询、详情数据        │
│  Elasticsearch    → 职位搜索(分词 + 相关度排序)            │
│  ChromaDB         → 向量检索(推荐系统语义召回, storage/)    │
│  Neo4j            → 知识图谱(技能关系、就业分析)            │
└──────────────────────────────────────────────────────────┘
```

**核心架构**：ES 是 MySQL 的「搜索副本」，**不存真相数据**。
所有写入只走 MySQL；ES 里的文档由同步脚本生成，**文档 `_id` = MySQL 主键**（天然幂等，重复同步不重复）。

**搜索链路（实际实现）**：

```
搜索请求 → 后端检查 SEARCH_ENGINE 开关(.env)
  ├─ es(默认): ES 查 id+排序 → MySQL 按 id 取详情 → 返回
  └─ mysql / ES异常: 自动降级 MySQL LIKE, 接口不受影响
```

代码位置：
| 组件 | 文件 |
|---|---|
| ES 客户端 | `app/core/es.py` |
| 搜索实现(multi_match + filter) | `app/services/jobs_service.py` → `_build_es_query` / `search_jobs_es` |
| 索引定义(mapping) | `scripts/init_es_index.py` |
| 全量同步脚本 | `scripts/sync_jobs_to_es.py` |

---

## 二、分词器配置

直接使用 IK 内置分词器（无自定义 analyzer）：

| 用途 | 分词器 | 说明 |
|---|---|---|
| **索引时**（写入文档） | `ik_max_word` | 最细粒度切分，保证任何搜索词都能命中 |
| **搜索时**（用户输入） | `ik_smart` | 智能切分，减少噪音召回 |

```
"资深Python后端工程师"
  ik_max_word → ["资深","python","后端","工程师","工程","师"]
  ik_smart    → ["资深","python","后端","工程师"]
```

**为什么索引细、搜索粗？** 索引时多切词确保"工程师/工程/师"各种搜索都能命中；搜索时少切词避免召回过多无关结果。

---

## 三、`jobs` 索引 Mapping（实际）

> 以 `scripts/init_es_index.py` 的 `MAPPING` 为单一真相源，本文同步维护。

### Settings

| 配置 | 值 | 说明 |
|---|---|---|
| `number_of_shards` | 1 | 单机部署 |
| `number_of_replicas` | 0 | 无副本节点，0 才是 green/yellow |

### 字段表（14 个字段）

| 字段 | 类型 | 分词器 | 说明 |
|---|---|---|---|
| **—— 全文搜索(text) ——** |
| `title` | text | ik_max_word / ik_smart | 职位标题，**搜索权重 ×3**（见下文） |
| `description_text` | text | ik_max_word / ik_smart | JD 纯文本 |
| `company_name` | text + `.keyword` 子字段 | ik_max_word / ik_smart | 公司名称（冗余自 companies，免 JOIN） |
| **—— 精确筛选(keyword，不分词) ——** |
| `skills` | keyword | — | 技能名数组（已归一的标准名，如 `["Python","MySQL"]`） |
| `city` | keyword | — | 城市 |
| `district` | keyword | — | 区县 |
| `industry_code` | keyword | — | 一级行业 code（同步时 `IT-RD` → `IT` 归一） |
| `experience_req` | keyword | — | 经验要求（**已在入库时归一 5 档**） |
| `education_req` | keyword | — | 学历要求（**已归一 5 档**） |
| `source` | keyword | — | 数据来源 |
| `job_status` | keyword | — | active / closed（对应 MySQL `status`） |
| **—— 范围字段 ——** |
| `salary_min` / `salary_max` | integer | — | 薪资区间（元/月） |
| `publish_at` | date | — | 发布时间（多 format 兼容） |

### 关键设计点

**1. 文档结构是"冗余拍平"的**

ES 不做 JOIN，company_name / skills 从 MySQL 关联表**平铺**进文档：

```
MySQL(3张表)                →  ES(1个文档)
jobs + companies + job_skills  { title, company_name, skills:[...], ... }
```

搜索命中后**回 MySQL 取完整详情**（`Job.id.in_(ids)` + 按 ES 顺序重排）——出参结构/前端完全无感。

**2. keyword vs text 的分工**

```
要"搜索"的字段(标题/JD/公司名)  → text + ik 分词(相关度匹配)
要"筛选"的字段(城市/学历/技能)  → keyword(整体精确匹配, 等价 WHERE city='北京')
```

**3. 归一化前置**

`education_req` / `experience_req` 依赖 MySQL 入库时 `@validates` 已归一的 5 档——ES 里直接 keyword 精确匹配，**查询侧零转换**。

**4. `industry_code` 同步时归一**

同步脚本把二级 `IT-RD` 截取为一级 `IT`（`split('-')[0]`），与统计口径一致。

---

## 四、典型查询（实际在用的）

### 4.1 职位搜索（`_build_es_query` 的实际形态）

```json
POST /jobs/_search
{
  "query": {
    "bool": {
      "must": [
        { "multi_match": {
            "query": "Python 后端",
            "fields": ["title^3", "skills", "company_name", "description_text"]
        }}
      ],
      "filter": [
        { "term": { "job_status": "active" } },
        { "term": { "city": "北京" } },
        { "term": { "education_req": "本科" } },
        { "range": { "salary_max": { "gte": 20000 } } }
      ]
    }
  },
  "sort": [{ "_score": "desc" }, { "publish_at": "desc" }],
  "from": 0, "size": 10
}
```

**must vs filter 的分工**：
- `must`（multi_match）→ 参与**相关度算分**，"谁更匹配"
- `filter`（term/range）→ 只过滤**不算分**，快且可缓存，"谁有资格出现"

**`title^3`**：标题命中得分 ×3——标题写"Python"的职位比正文提一句的排更前。

### 4.2 排序规则

| 场景 | 排序 |
|---|---|
| 有关键词 | `_score` 相关度优先，同分看新鲜度 |
| 无关键词 + sort=salary | `salary_max` 倒序 |
| 无关键词（默认/最新） | `publish_at` 倒序 |

---

## 五、数据同步（实际方案）

### 5.1 同步方式：全量重建（幂等）

```
MySQL(真相源) --sync_jobs_to_es--> ES jobs 索引
                    文档 _id = MySQL 主键
                    重复跑 → 覆盖同 id 文档, 不产生重复
```

**两个入口**：
| 入口 | 命令/操作 | 场景 |
|---|---|---|
| 一键全库同步（推荐） | 数据管理页点按钮 / `POST /crawl/sync-all` | 爬虫导入新数据后，四库(MySQL→ES→Chroma→Neo4j)一条龙 |
| 手动脚本 | `python -m scripts.init_es_index && python -m scripts.sync_jobs_to_es` | 调试 / 只重建 ES |

### 5.2 增量说明

当前为**全量同步**（1 万条约几秒）。爬虫新增数据后跑一次同步即可。
（规划中的简历入库单条 `es_client.index()` 增量、Outbox 双写暂未实现，数据量大后再上。）

### 5.3 软删除

同步时按 `is_deleted=0` 过滤，ES 中不含已删除数据（重建索引时自然清除）。

---

## 六、运维备忘（实际踩过的坑）

| 事项 | 说明 |
|---|---|
| **启动** | `C:\RJ\elasticsearch-9.4.2\bin\elasticsearch.bat`（窗口别关），验证 `GET :9200` |
| **安全认证** | 已关闭（`xpack.security.enabled: false`），Python 免密直连 |
| **⚠️ 磁盘水位** | C 盘 >85% 会触发 ES 高水位 → 分片下线集群 red、写入被拒。已把水位调到 95/97/99%（persistent）。**磁盘紧张时先清理 C 盘** |
| **客户端超时** | 8.15 客户端连 9.4 服务端偶发"请求成功但等响应超时"，`es.py` 已配 `retry_on_timeout` + `max_retries=3` |
| **近实时性** | 写入后 ~1 秒才可搜（refresh interval），count 与刚写入条数短暂不一致是正常现象 |
| **索引重建** | `init_es_index` 会**先删后建**（开发期方便改 mapping，生产应走 alias 平滑迁移） |

---

## 附：规划中未实现的能力

以下在早期设计（`db/es/*.json`）中规划、**当前未实现**，需要时再启用：

- `resumes` / `companies` 独立索引（当前简历检索走 ChromaDB 向量、公司信息冗余在 jobs 文档）
- `title.suggest`（completion 类型）搜索框自动补全
- `location`（geo_point）地理范围搜索
- 自定义 analyzer（当前用 IK 内置 + ES 默认 lowercase）

---

**文档版本**：v2.0（对齐实际实现）
**对应代码**：`app/core/es.py`、`scripts/init_es_index.py`、`scripts/sync_jobs_to_es.py`、`app/services/jobs_service.py`
**维护约定**：改 mapping / 同步逻辑 / 搜索实现时同步更新本文档
