# 岗位推荐功能方案 (简历 → 岗位智能匹配)

> **依赖**：MySQL(主数据) + ChromaDB(向量库) + 智谱 GLM(embedding-3 向量化 / glm-4-flash 重排)
> **后端接口**：`GET /recommend?resume_id=` (需 JWT)
> **前端页面**：`/job-recommend` (导航栏"岗位推荐")
> **定位**：推荐系统核心功能——上传简历后一键匹配岗位，带匹配分和 AI 推荐理由
> **生成时间**：2026-08-23

---

## 目录

- [一、功能在项目中的定位](#一功能在项目中的定位)
- [二、三段式推荐管线](#二三段式推荐管线)
- [三、双路召回详解](#三双路召回详解)
- [四、打分融合与 LLM 重排](#四打分融合与-llm-重排)
- [五、文件清单](#五文件清单)
- [六、API 契约](#六api-契约)
- [七、向量库建设与维护](#七向量库建设与维护)
- [八、配置与依赖](#八配置与依赖)
- [九、数据落库(推荐流水)](#九数据落库推荐流水)
- [十、与其他模块的边界](#十与其他模块的边界)

---

## 一、功能在项目中的定位

用户在"我的简历"上传并解析简历后，进入"岗位推荐"页选择一份简历，
系统从全量在招岗位中找出最匹配的 10 个，每个岗位给出：

- **匹配分**(0~100)：综合技能命中 + 语义相似度 + LLM 判断
- **推荐理由**(一句话中文)：由大模型生成，如"技能高度契合，NLP和大模型经验丰富"

与其他存储的分工：

```
MySQL           职位/简历/技能主数据(技能召回用)
ChromaDB        职位 JD 向量(语义召回用, 本功能自建)
智谱 GLM        embedding-3(JD/简历向量化) + glm-4-flash(重排+理由)
```

> 注意：本功能**直连**智谱 API(`app/core/llm.py`)，不经过 LLM 简历解析服务(LLM_SERVICE_URL)。
> 两者关系见 [十、与其他模块的边界](#十与其他模块的边界)。

---

## 二、三段式推荐管线

业界经典「召回 → 打分 → 重排」结构，核心入口 `recommend_service.recommend()`:

```
用户选择简历 (resume_id)
        │
        ▼
┌─────────────────── 召回(RECALL) ───────────────────┐
│  路A: 技能召回(recall_by_skills)   路B: 向量召回(recall_by_vector)  │
│  SQL 技能交集命中, 加权排序          简历→向量→ChromaDB 语义 top30    │
└────────────────────────┬───────────────────────────┘
                         ▼
              融合(SCORE): 按 job_id 求并集, 分数取 max
                         ▼
              粗排取 top 15 → 送 LLM 重排(rerank_with_llm)
                         ▼
              glm-4-flash 逐岗位打分(0~100) + 生成推荐理由
                         ▼
              按最终分排序, 返回前 10 条 + 写推荐流水
```

关键常量(在 `recommend_service.py` 顶部)：

| 常量 | 值 | 含义 |
|---|---|---|
| `_RECALL_TOP_N` | 30 | 每路召回拉多少候选 |
| `_RERANK_TOP_K` | 15 | 送 LLM 重排的候选数(prompt 太长模型会忽略后段) |
| `_RETURN_TOP_N` | 10 | 最终返回给前端的条数 |
| `_MAX_SKILLS_FOR_NORMALIZE` | 5 | 技能分归一化基数(封顶防虚高) |

---

## 三、双路召回详解

### 路A: 技能召回 `recall_by_skills` — 精确匹配

```
简历技能集 [Python, MySQL, Redis]
   → 查 job_skills 表中 skill_id 命中的行
   → 按 job_id 分组数命中数
   → 加权排序: is_must=1 的命中算 2 分, 普通命中算 1 分
   → 只取 status=active 且未删除的岗位, top 30
```

特点：准、快、可解释，但只能匹配"技能字典里字面相同"的技能。

### 路B: 向量召回 `recall_by_vector` — 语义匹配

```
1. 简历拼"求职文本" = 求职意向 + 技能名 + 前2段工作经历摘要
2. GLM embedding-3 转成 2048 维向量
3. ChromaDB job_jd 集合查余弦相似度 top 30
4. 回 SQL 把 job_id 批量转成完整 Job 对象(预加载 company/skills)
```

特点：懂语义，能把"会 Python 的人"和"招后端开发的岗位"关联起来，
弥补路A 字面匹配的盲区。

> **为什么两路都要**: 技能召回准但覆盖窄，向量召回广但可能有噪音，
> 并集 + 后续 LLM 精排 = 兼顾覆盖与精度。

---

## 四、打分融合与 LLM 重排

### 融合规则(量纲统一到 0~100)

| 信号 | 计算方式 |
|---|---|
| 技能分 | `min(命中技能数, 5) / 5 × 100` |
| 向量分 | `相似度(0~1) × 100`(ChromaDB 距离换算: score = 1 − dist/2) |
| 融合分 | `max(技能分, 向量分)` — 召回阶段求"全"，某一路强就该进候选 |

### LLM 重排 `rerank_with_llm`(glm-4-flash)

把简历摘要 + top15 候选岗位(标题/城市/技能/要求摘要)拼进 prompt，
让模型逐岗位输出 JSON: `{job_id, score(0~100), reason(一句话理由)}`。

**为什么需要 LLM**: 向量是"文本相似"，但"近"≠"合适"
(比如简历要北京、岗位在深圳)。LLM 能理解这类硬约束，
并给出可解释的推荐理由——这是向量给不出的。

**降级策略(关键)**: LLM 返回非法 JSON / 超时 / 限流时，
任何失败都自动回退到融合分，reason 用默认文案"技能与经验较为匹配"。
原则：**用户看到推荐结果比 LLM 完美工作更重要**，推荐绝不因 LLM 抖动而崩。

---

## 五、文件清单

| 文件 | 职责 |
|---|---|
| `app/core/llm.py` | 智谱 GLM 客户端(chat/chat_json/embed/embed_batch + async 包装, SDK 异常转译) |
| `app/services/vector_service.py` | ChromaDB 封装(job_jd 集合读写, 距离→相似度换算) |
| `app/services/recommend_service.py` | 推荐核心管线(召回/融合/重排/落库) |
| `app/api/recommend.py` | `GET /recommend` 路由(JWT + 简历归属校验) |
| `app/schemas/recommend.py` | 出参 Schema(RecommendItem/RecommendOut) |
| `scripts/build_job_vectors.py` | 建库脚本(MySQL 职位 → 向量库, 增量) |
| `frontend/src/views/RecommendView.vue` | 推荐页(选简历→出结果, 复用 JobCard) |

改动的现有文件(均为最小侵入):

| 文件 | 改动 |
|---|---|
| `app/core/config.py` | +ZHIPU_* 配置字段 + CHROMA_PATH 属性 |
| `app/api/__init__.py` | +recommend_router 注册 |
| `requirements.txt` | +zhipuai(chromadb 原本就有) |
| `.env` / `.env.example` | +ZHIPU_API_KEY |
| `frontend/src/router/index.js` | +/job-recommend 路由 |
| `frontend/src/components/layout/AppHeader.vue` | +导航入口"岗位推荐" |

---

## 六、API 契约

```
GET /recommend?resume_id=1
Authorization: Bearer <token>
```

响应(统一 Result 包裹):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "job":        { "id": 1, "title": "...", "city": "...", "company": {}, "skills": [] },
        "score":      95.0,
        "reason":     "技能高度契合，NLP和大模型经验丰富",
        "strategy":   "rag"
      }
    ],
    "total": 10,
    "strategy": "rag"
  }
}
```

| 错误场景 | 表现 |
|---|---|
| 未登录 | 401(JWT 拦截) |
| resume_id 不存在 / 不是本人的简历 | code=103 "简历不存在或无权访问" |
| 简历没技能且向量库无匹配 | 正常返回空列表(items=[], total=0) |

**strategy 字段含义**(写入推荐流水, 供效果对比):

| 值 | 含义 |
|---|---|
| skill | 纯技能召回(未用向量/LLM) |
| hybrid | 技能 + 向量双路召回 |
| rag | 全链路: 双路召回 + LLM 重排(当前线上策略) |

---

## 七、向量库建设与维护

**首次建库 / 增量更新**(在 backend/ 目录下):

```bash
python -m scripts.build_job_vectors            # 增量: 跳过已存在的, 只建新职位
python -m scripts.build_job_vectors --rebuild  # 全量重建(先清空)
python -m scripts.build_job_vectors --limit 5  # 只建前5条(调试)
```

- JD 文本拼接 = **标题 + 技能名 + JD 正文**(技能词放前段, embedding 对前段更敏感)
- 批量向量化: 每批 20 条, 一次请求省网络往返
- 存储位置: `backend/storage/chroma/`(文件型, 无需额外数据库服务)
- 集合: `job_jd`, 余弦相似度, embedding-3 默认 2048 维

> ⚠️ **重要**: 爬虫导入了新职位后, 需要重跑一次建库脚本(增量模式只对新职位算向量, 费用极低),
> 否则新职位只进技能召回、不进向量召回。

---

## 八、配置与依赖

`.env` 需要新增(其他 ZHIPU_* 有默认值可不配):

```env
ZHIPU_API_KEY=你的智谱Key   # https://open.bigmodel.cn 申请
```

依赖(`requirements.txt` 已更新, 需 `pip install -r requirements.txt`):

```
zhipuai     # 智谱官方 SDK
chromadb    # 向量库(Windows 安装: pip install --only-binary :all: chromadb)
```

费用参考: glm-4-flash 免费; embedding-3 约 0.5 元/百万 token,
10000 条 JD 全量建库一次性约 2~3 元, 单次推荐的查询向量费用可忽略。

---

## 九、数据落库(推荐流水)

每次推荐成功, 每个结果写一行 `recommendations` 表(复用现有表, 无需改表):

| 字段 | 内容 |
|---|---|
| user_id / resume_id / job_id | 谁用哪份简历匹配了哪个岗位 |
| score | 最终分(LLM 分或降级后的融合分) |
| reason | 推荐理由(LLM 生成或默认文案) |
| strategy | "rag"(当前固定, 预留策略对比) |
| snapshot | JSON, 完整记录分数推导链路 |

`snapshot` 示例(排查"为什么给我推这个"时直接看这里):

```json
{
  "skill_score":  80.0,
  "vector_score": 62.5,
  "fused_score":  80.0,
  "llm_score":    95.0,
  "hit_skill_count": 4
}
```

---

## 十、与其他模块的边界

| 模块 | 关系 |
|---|---|
| LLM 简历解析服务(LLM_SERVICE_URL) | **不依赖**。简历解析仍走原服务(`/agents/analyze-resume`), 本功能只读取解析产出的 resume_skills 等表 |
| AI 求职顾问(前端 /recommend, ChatView) | **互不影响**。前端路由错开: 聊天页用 /recommend, 岗位推荐用 /job-recommend |
| 知识图谱(Neo4j) | **不依赖**。本功能 = MySQL + ChromaDB + GLM 三件套, 图谱增强属未来可选项 |
| 我的简历(ResumeManage) | 上游。简历需先解析成功(parse_status=done)才有技能可用于召回 |

---

## 附: 快速体验路径

1. 启动后端(`python run.py`) + 前端(`npm run dev`)
2. 登录 → "我的简历"上传 PDF 简历(等待解析完成)
3. 导航栏点"岗位推荐" → 选简历 → 点"开始推荐"
4. 查看带匹配分、金银铜排名徽章、AI 推荐理由的岗位列表, 点卡片跳职位详情
