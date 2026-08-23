# 知识图谱功能方案 (Neo4j)

> **数据库**：Neo4j 5.x (bolt://localhost:7687)
> **Python 驱动**：py2neo / neo4j 官方驱动
> **定位**：推荐系统的"增强插件" + 数据分析的关系挖掘
> **生成时间**：2026-07-20

---

## 目录

- [一、知识图谱在项目中的定位](#一知识图谱在项目中的定位)
- [二、四大核心功能](#二四大核心功能)
- [三、节点设计](#三节点设计)
- [四、关系设计](#四关系设计)
- [五、Cypher 查询模板](#五cypher-查询模板)
- [六、数据同步方案 (MySQL → Neo4j)](#六数据同步方案-mysql--neo4j)
- [七、对外暴露的 API](#七对外暴露的-api)
- [八、落地路线](#八落地路线)
- [九、依赖与配置](#九依赖与配置)

---

## 一、知识图谱在项目中的定位

知识图谱在 JobHunter 项目里**不是独立功能**,而是服务于两个核心场景:

| 场景 | 价值 | 对接前端 |
|---|---|---|
| **推荐系统增强** | 拓展技能集 / 跨技能匹配 | `Recommend.vue` (strategy=graph) |
| **数据分析可视化** | 技能共现 / 中心性 / 关系网络 | `Dashboard.vue` 的图表区 |

### 与其他存储的分工

```
MySQL           结构化主数据(精确查询, "数据源头")
Elasticsearch   全文模糊搜索(关键词级)
ChromaDB        向量语义匹配(意思级, RAG 用)
Neo4j           关系网络推理(多跳关系, "关系挖掘")
```

**核心原则**: MySQL 是事实数据的源头, Neo4j 是从 MySQL 同步过来的"关系视图",
**Neo4j 不存独有数据, 只存关系**。

---

## 二、四大核心功能

### 功能 1:推荐系统的技能拓展 (最高价值 ⭐⭐⭐⭐⭐)

**问题**: 用户简历技能 `[Python, Django]`, 职位要 `[Go, 微服务]`,
按关键词完全不匹配, 但图谱知道它们语义相近 → 仍可推荐。

```
用户简历技能: [Python, Django]
       ↓
图谱查询: 这些技能的"近邻"是什么?
       ↓
(Python)─SIMILAR_TO─(Go)         ← 都是后端语言
(Django)─ECOSYSTEM─(微服务)      ← 同属 Web 后端生态
       ↓
拓展后技能集: [Python, Django, Go, 微服务]
       ↓
匹配度从 20% 提升到 65%, 推荐出原本漏掉的职位
```

**对接前端**: `Recommend.vue` 的 `missing_skills` / `matched_skills` 都靠图谱算出来。

---

### 功能 2:技能共现挖掘 (Dashboard 数据分析 ⭐⭐⭐⭐)

Dashboard 的"热门技能 TOP 15"纯计数很无聊, 用图谱能挖出**技能共现关系**:

```
"会 Python 的人, 通常还会?"
    ↓
MATCH (p:Skill {name:'Python'})<-[:HAS_SKILL]-(r)-[:HAS_SKILL]->(s:Skill)
RETURN s.name, COUNT(*) AS freq
ORDER BY freq DESC LIMIT 10
    ↓
结果: Django(78%), MySQL(72%), Docker(58%), Git(55%)...
    ↓
做成"技能共现图谱"可视化, 比柱状图有意思 100 倍
```

**对接前端**: `Dashboard.vue` 的热门技能图表, 升级为关系网络图。

---

### 功能 3:职业路径推理 (潜在功能 ⭐⭐⭐)

```
(初级Python) ─NEXT─> (中级Python) ─NEXT─> (高级Python) ─NEXT─> (架构师)
                                                    ↑
                            (DevOps)  ─CROSSOVER─> (架构师)
```

图谱能回答"我这个技能栈下一步能往哪走", 给求职者方向建议。

**对接前端**: 可放在 Recommend 页或 Profile 页(加分项, 非必须)。

---

### 功能 4:技能归一 (简历/职位解析时 ⭐⭐)

```
简历里抽到: "Py3" "python3.x" "Python3"
       ↓
图谱查询: 这些都是 (Python) 的别名
       ↓
归一到标准技能: Python (skill_id=5)
```

**说明**: 这就是 schema 文档里 `skills.alias` 字段的图实现。
**但此功能 MySQL 也能做** (alias 字段直接 LIKE), 图谱不是必需。

---

## 三、节点设计

### 4 种节点

| 节点标签 | 含义 | 唯一标识 | 示例 |
|---|---|---|---|
| `Skill` | 技能节点 | `skill_code` | Python, Django, MySQL |
| `Job` | 职位节点 | `job_code` | 高级Python工程师 |
| `Company` | 公司节点 | `company_code` | 阿里巴巴 |
| `Resume` | 简历节点 | `resume_code` | 张三的简历 |

### 节点属性

```cypher
// 技能节点
(:Skill {
  skill_code: 'SK_PY',
  name: 'Python',
  category: '语言',
  is_hot: 1,
  weight: 0.95        // 全局重要性(可由 PageRank 算)
})

// 职位节点
(:Job {
  job_code: 'J_xxx',
  title: '高级Python工程师',
  city: '北京',
  salary_max: 40000,
  source: 'boss'
})

// 公司节点
(:Company {
  company_code: 'C_xxx',
  name: '阿里巴巴',
  short_name: '阿里',
  industry_code: 'IT'
})

// 简历节点
(:Resume {
  resume_code: 'R_xxx',
  name: '张三',
  work_years: 5,
  expect_city: '北京'
})
```

### 命名规范

- 节点标签用 **PascalCase**: `Skill`, `Resume`
- 节点属性用 **snake_case**: `skill_code`, `work_years`
- **唯一标识对齐 MySQL 的 `*_code` 字段**, 方便回查

---

## 四、关系设计

### 6 种关系

| 关系类型 | 方向 | 含义 | 来源 | 性质 |
|---|---|---|---|---|
| `HAS_SKILL` | Resume → Skill | 简历拥有技能 | resume_skills 表 | **事实** |
| `REQUIRES` | Job → Skill | 职位要求技能 | job_skills 表 | **事实** |
| `BELONGS_TO` | Job → Company | 职位属于公司 | jobs.company_id | **事实** |
| `WORKED_AT` | Resume → Company | 简历工作过的公司 | resume_experiences 表 | **事实** |
| `SIMILAR_TO` | Skill → Skill | 技能相似(核心!) | 离线算法算 | **推理** |
| `CO_OCCURRED` | Skill → Skill | 技能共现 | 离线统计 | **推理** |

### 关系属性

```cypher
// HAS_SKILL: 简历→技能, 带熟练度
()-[:HAS_SKILL {proficiency: 4, years: 3.5}]->()

// REQUIRES: 职位→技能, 带权重和必须性
()-[:REQUIRES {weight: 1.5, is_must: 1}]->()

// SIMILAR_TO: 技能→技能, 带相似度
()-[:SIMILAR_TO {weight: 0.85, reason: '同属后端语言'}]->()

// CO_OCCURRED: 技能→技能, 带共现频次
()-[:CO_OCCURRED {count: 156, ratio: 0.78}]->()
```

### 关系图示例

```
                    HAS_SKILL(weight=0.9)
        ┌────────────────────────────────┐
        ▼                                ▼
    (Python)  ──SIMILAR_TO──>  (Go)      ← 推理关系(离线算)
        │                                │
   REQUIRES                          REQUIRES
        │                                │
        ▼                                ▼
    (Job:Py工程师)                 (Job:Go工程师)
        │                                │
        └──────── BELONGS_TO ────────────┘
                                         ▲
                                         │
(Python)  <──HAS_SKILL──  (Resume:张三)  ──WORKED_AT──> (Company:阿里)
```

---

## 五、Cypher 查询模板

### 5.1 拓展技能集 (推荐系统核心查询)

```cypher
// 输入: 一个技能名, 找它最相似的 N 个技能
MATCH (s:Skill {name: $skill_name})-[r:SIMILAR_TO]->(sim:Skill)
WHERE r.weight > 0.5
RETURN sim.name AS skill, r.weight AS similarity
ORDER BY r.weight DESC
LIMIT $limit
```

### 5.2 技能共现分析 (Dashboard)

```cypher
// 查"会 X 的人通常还会什么技能"
MATCH (target:Skill {name: $name})<-[:HAS_SKILL]-(r:Resume)-[:HAS_SKILL]->(other:Skill)
WHERE other <> target
RETURN other.name AS skill,
       count(*) AS freq,
       count(*) * 1.0 / total_resumes AS ratio
ORDER BY freq DESC
LIMIT 10
```

### 5.3 跨技能匹配 (推荐系统)

```cypher
// 用户有 Python, 找要求"相似技能"的职位
MATCH (r:Resume {resume_code: $code})-[:HAS_SKILL]->(base:Skill)
MATCH (base)-[:SIMILAR_TO*1..2]->(related:Skill)<-[:REQUIRES]-(j:Job)
WHERE j.status = 'active'
RETURN DISTINCT j, collect(related.name) AS matched_via
ORDER BY length(matched_via) DESC
```

### 5.4 技能中心性 (PageRank 找"核心技能")

```cypher
// 调用 GDS 库跑 PageRank, 找最重要的技能节点
CALL gds.pageRank.stream('skillGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS skill, score
ORDER BY score DESC
LIMIT 15
```

### 5.5 技能归一 (简历解析时)

```cypher
// 抽取到的"Py3"归一到标准技能 Python
MATCH (s:Skill)
WHERE $alias IN s.aliases OR s.name = $alias
RETURN s.skill_code AS standard_code, s.name AS standard_name
LIMIT 1
```

### 5.6 职业路径 (推理功能)

```cypher
// 从当前技能出发, 找职业演进路径
MATCH path = (cur:Skill {name: $name})-[:NEXT*1..3]->(future:Skill)
RETURN [n IN nodes(path) | n.name] AS career_path,
       length(path) AS steps
ORDER BY steps
```

---

## 六、数据同步方案 (MySQL → Neo4j)

### 同步策略

| 方案 | 说明 | 适用阶段 |
|---|---|---|
| **同步双写** | 简历解析完成 / 爬虫入库时, 直接写 Neo4j | MVP 推荐 |
| **定时全量** | 每天/每小时全量同步 | 数据量稳定后 |
| **CDC 监听** | 监听 MySQL binlog, 自动同步 | 生产环境 |

### 同步代码骨架

```python
# services/graph_sync_service.py
from py2neo import Graph, Node, Relationship

graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))


async def sync_resume_to_graph(resume, db):
    """简历解析完成后, 同步到知识图谱。

    关键: 全程用 MERGE(存在则更新, 不存在则创建), 避免重复同步产生重复节点。
    """
    # 1. 创建简历节点
    graph.run("""
        MERGE (r:Resume {resume_code: $code})
        SET r.name = $name,
            r.work_years = $years,
            r.expect_city = $city
    """, code=resume.resume_code, name=resume.name,
         years=resume.work_years, city=resume.expect_city)

    # 2. 建 HAS_SKILL 关系
    for rs in resume.skills:
        graph.run("""
            MERGE (s:Skill {skill_code: $skill_code})
            WITH s
            MATCH (r:Resume {resume_code: $resume_code})
            MERGE (r)-[rel:HAS_SKILL]->(s)
            SET rel.proficiency = $prof,
                rel.years = $years
        """, skill_code=rs.skill.skill_code,
             resume_code=resume.resume_code,
             prof=rs.proficiency, years=rs.years)


async def sync_job_to_graph(job, db):
    """爬虫入库后, 同步到知识图谱。"""
    # 1. 创建职位节点
    graph.run("""
        MERGE (j:Job {job_code: $code})
        SET j.title = $title, j.city = $city
    """, code=job.job_code, title=job.title, city=job.city)

    # 2. 建 REQUIRES 关系
    for js in job.skills:
        graph.run("""
            MERGE (s:Skill {skill_code: $skill_code})
            WITH s
            MATCH (j:Job {job_code: $job_code})
            MERGE (j)-[rel:REQUIRES]->(s)
            SET rel.weight = $weight,
                rel.is_must = $must
        """, skill_code=js.skill.skill_code,
             job_code=job.job_code,
             weight=float(js.weight or 1), must=js.is_must)
```

### SIMILAR_TO 关系的离线计算

```python
# scripts/compute_skill_similarity.py
"""
定时任务: 离线计算技能相似度, 写入 SIMILAR_TO 关系。

算法: 基于共现的 Jaccard 相似度
    similarity(A, B) = |同时拥有 A 和 B 的简历数| / |拥有 A 或 B 的简历数|
"""
def compute_skill_similarity():
    # 1. 查询所有技能对共现次数
    pairs = graph.run("""
        MATCH (s1:Skill)<-[:HAS_SKILL]-(r)-[:HAS_SKILL]->(s2:Skill)
        WHERE s1 < s2
        RETURN s1.skill_code AS a, s2.skill_code AS b, count(*) AS cooccur
    """).data()

    # 2. 算 Jaccard 相似度
    for p in pairs:
        jaccard = p['cooccur'] / (count_skill(p['a']) + count_skill(p['b']) - p['cooccur'])
        if jaccard > 0.1:   # 阈值, 过滤弱关联
            graph.run("""
                MATCH (a:Skill {skill_code: $a}), (b:Skill {skill_code: $b})
                MERGE (a)-[r:SIMILAR_TO]->(b)
                SET r.weight = $w
            """, a=p['a'], b=p['b'], w=jaccard)
```

---

## 七、对外暴露的 API

### API 1:推荐时拓展技能 (核心)

```python
# api/recommendations.py (待做)
@router.get("/recommendations")
async def recommend(resume_id: int, db = Depends(get_db)):
    # 1. 拿简历技能
    resume = await db.get(Resume, resume_id)
    skill_codes = [rs.skill.skill_code for rs in resume.skills]

    # 2. 查图谱, 拓展近邻技能 ← 知识图谱发力点!
    extended = graph_dao.find_neighbor_skills(skill_codes, depth=2)

    # 3. 用拓展集去 MySQL 匹配职位
    matched_jobs = await query_jobs_by_skills(db, extended)

    # 4. 算分排序返回
    ...
```

### API 2:技能共现分析 (Dashboard)

```python
# api/stats.py (待做)
@router.get("/stats/skills/co-occurrence")
async def skill_cooccurrence(skill_name: str):
    """查和某技能共现最多的技能(用于技能图谱可视化)。"""
    return graph_dao.find_cooccurrence(skill_name)
```

### API 3:技能相似查询

```python
@router.get("/skills/{name}/similar")
async def similar_skills(name: str):
    """查某技能的相似技能(用于推荐时展示"换相似技能搜")。"""
    return graph_dao.find_similar_skills(name)
```

---

## 八、落地路线

### 阶段 1:搭骨架 (必做)

```
1. Neo4j 环境搭建 + py2neo/neo4j 驱动连通
2. 设计节点和关系(4 节点 + 6 关系)
3. 写 graph_dao.py 基础封装
4. 简历/职位数据同步脚本(从 MySQL 灌入 Neo4j)
```

### 阶段 2:核心价值 (强烈建议)

```
5. 实现 SIMILAR_TO 关系(用共现算法离线算)
6. 推荐接口用图谱拓展技能 ← 真正的项目亮点
```

### 阶段 3:锦上添花 (看时间)

```
7. Dashboard 加"技能图谱"可视化
8. 职业路径推理(可选)
9. 技能归一辅助(可选, MySQL 也能做)
```

---

## 九、依赖与配置

### requirements.txt 新增

```
py2neo==2021.2.4             # Pythonic 的 Neo4j 客户端(适合 MVP)
neo4j==5.25.0                # 官方驱动(性能更好, 支持异步)
```

### config.py 新增

```python
class Settings(BaseSettings):
    ...
    # ---------- Neo4j ----------
    NEO4J_URI: str = Field(default="bolt://127.0.0.1:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="jobhunter")
    NEO4J_DATABASE: str = Field(default="neo4j")    # 社区版只有默认库
```

### .env 示例

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 数据库连接

```python
# app/core/graph.py
from py2neo import Graph
from app.core.config import settings

graph = Graph(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    name=settings.NEO4J_DATABASE,
)
```

---

## 十、性能与运维注意事项

### 1. 数据基础是前提

知识图谱要发挥作用, **MySQL 里得先有数据**:
- 没有简历数据 → `HAS_SKILL` 关系建不起来
- 没有职位数据 → `REQUIRES` 关系建不起来
- 没有几十份简历/职位 → 共现统计算不准

**建议**: 先用 mock 数据灌一批进 Neo4j 做演示。

### 2. MERGE 防 I/O 竞争

同步代码**必须用 `MERGE`**, 不能用 `CREATE`:
- `CREATE` 每次都新建节点 → 重复同步会产生重复节点
- `MERGE` 存在则更新, 不存在则创建 → 幂等

### 3. 性能边界

Neo4j 对**多跳查询**有优势, 但**单点查询单条不一定比 MySQL 快**。
图谱的价值在"关系推理", 不是"简单查询"。

### 4. 不要一上来追求完美

图谱可以迭代:
- **MVP**: 只建 Skill 节点 + HAS_SKILL + REQUIRES, 能跑推荐拓展
- **进阶**: 加 SIMILAR_TO(离线算)
- **高级**: 加 PageRank 中心性、社区发现等算法

---

## 附:与其他存储的边界

| 场景 | 用 MySQL | 用 Neo4j |
|---|---|---|
| 按 ID 查单个职位/简历 | ✅ | ❌ 杀鸡用牛刀 |
| 按条件筛选列表 | ✅ | ❌ |
| 关键词模糊搜索 | ✅ LIKE | ❌ |
| 全文检索 | ❌ | ❌(用 ES) |
| 语义匹配 | ❌ | ❌(用 ChromaDB 向量库) |
| 多跳关系推理 | ❌(SQL 写吐血) | ✅ **天生擅长** |
| 技能共现/中心性 | ❌(JOIN 多到爆) | ✅ |
| 跨技能推荐 | ❌ | ✅ |

**核心原则**: **MySQL 是"属性查询"的主场, Neo4j 是"关系推理"的主场**。

---

**文档版本**: v1.0
**对应数据库**: Neo4j 5.x
**对应 schema 文档**: `backend/db/DATABASE_SCHEMA.md`
**维护建议**: Neo4j schema 变更需同步更新本文档
