# 岗能智绘——多源异构数据驱动岗位能力动态图谱平台

## 大模型智能引擎模块（llm_module）

> **模块定位**：平台的大模型智能引擎，负责从多源异构数据中抽取岗位能力知识、构建和补全岗位能力知识图谱、提供智能问答和推理服务、支撑岗位能力动态演化分析。

---

## 一、项目概述

**岗能智绘**是一个基于多源异构数据驱动的岗位能力动态图谱平台，利用大语言模型（LLM）结合知识图谱技术，实现岗位能力的智能分析、差距诊断、学习路径规划和趋势预测。

### 核心能力

- **岗位能力知识抽取**：从招聘网站、行业报告、政策文件等异构数据源中自动提取岗位、技能、能力等实体及关联关系
- **动态知识图谱构建**：基于 Neo4j 构建时序知识图谱，支持岗位能力的动态演化追踪
- **智能问答与推理**：通过 RAG 检索增强与图谱推理实现高精度人岗匹配诊断
- **多智能体协同分析**：1个 Master Agent + 5个专业子Agent协同工作，提供深度分析
- **全景可视化交互**：支撑 AntV G6 和 ECharts 实现知识图谱可视化

---

## 二、系统架构

### 2.1 四层架构概览

```
┌─────────────────────────────────────────────────────────────┐
│  第四层：用户交互层                                           │
│  ├── RESTful API 接口（完整分析请求 / 结果返回）              │
│  └── WebSocket 流式接口（实时进度推送 + 打字机效果输出）       │
├─────────────────────────────────────────────────────────────┤
│  第三层：Agent 协同层                                         │
│  ├── Master Agent（总调度官：意图识别 · 任务分解 · 结果汇总） │
│  ├── 岗位分析 Agent（行业研究员）                             │
│  ├── 能力差距分析 Agent（能力评估师）                         │
│  ├── 学习路径规划 Agent（职业规划师）                         │
│  ├── 趋势预测分析 Agent（趋势分析师）                         │
│  ├── 报告生成 Agent（报告撰写人）                             │
│  ├── 工作流引擎（任务分解 → 条件路由 → 链式/并行调用 → 汇总）  │
│  └── 记忆系统（短期对话记忆 + 长期用户画像）                   │
├─────────────────────────────────────────────────────────────┤
│  第二层：工具层 Tools                                         │
│  ├── 知识图谱查询工具 → Neo4j 图数据库                        │
│  ├── RAG 检索工具 → ChromaDB 向量数据库                       │
│  └── 数据库查询工具 → MySQL / SQLite                          │
├─────────────────────────────────────────────────────────────┤
│  第一层：大模型基座层                                         │
│  ├── 主力模型：智谱 GLM-4 系列（云端API · 强推理）            │
│  ├── 备选模型：DeepSeek / 通义千问 / Kimi / 讯飞星火          │
│  ├── 降级策略：主力不可用时自动切换备选                       │
│  └── 模型路由：根据任务复杂度分级选择模型                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 项目目录结构

```
llm_module/
├── api/                          # API接口层 (FastAPI)
│   ├── main.py                   # FastAPI主入口 + 根路由
│   ├── agent_routes.py           # Agent协同层API路由 (/agents/*)
│   └── v1/                       # 版本化RESTful API (/api/v1/*)
│       ├── routes.py             # 会话/对话/工作流/管理/监控接口
│       ├── auth_routes.py        # 用户认证注册 (JWT)
│       └── health_routes.py      # 增强健康检查
│
├── agents/                       # Agent协同层
│   └── agent_coordinator.py      # Master Agent + 5子Agent + 工作流引擎 (91KB)
│
├── core/                         # 核心逻辑
│   ├── extractor.py              # 知识抽取（NER + LLM）
│   ├── kg_builder.py             # 知识图谱构建 + 校验/推理
│   ├── qa_engine.py              # 问答引擎（支持RAG）
│   ├── data_pipeline.py          # 数据预处理管道
│   └── error_handler.py          # 容错兜底（重试/降级/熔断）
│
├── models/                       # 数据模型
│   ├── schemas.py                # Pydantic数据模型 + 本体约束
│   └── prompts.py                # LLM提示词模板
│
├── services/                     # 业务服务层（16个服务）
│   ├── llm_service.py            # 大模型调用（6家提供商/智能路由/降级）
│   ├── rag_service.py            # RAG检索增强（混合检索/重排序）
│   ├── vector_store.py           # ChromaDB向量存储
│   ├── db_service.py             # MySQL/SQLite数据库
│   ├── neo4j_service.py          # Neo4j图数据库
│   ├── es_service.py             # Elasticsearch搜索
│   ├── auth_service.py           # JWT认证
│   ├── metrics_service.py        # 监控指标 + 告警引擎
│   ├── trace_service.py          # 全链路追踪
│   ├── evaluation_service.py     # 自动化评价
│   ├── feedback_optimizer.py     # 低分反馈优化
│   ├── prompt_optimizer.py       # Prompt工程优化
│   ├── quality_service.py        # 质量评分（LLM-as-Judge）
│   ├── quota_service.py          # 资源配额限制
│   ├── ab_test_service.py        # A/B测试框架
│   ├── tool_executor.py          # 工具执行器（6个内置工具）
│   └── persistence_service.py    # JSON持久化
│
├── frontend/                     # Vue 3 前端
│   ├── package.json              # 依赖（vue 3 + vue-router 4 + vite 5）
│   ├── vite.config.js            # Vite构建配置（API代理到5173）
│   └── src/
│       ├── views/                # 页面：ChatView 聊天 / AdminView 管理
│       ├── components/           # 组件（chat/ + admin/ + common/）
│       ├── api/index.js          # API调用封装
│       ├── composables/          # 组合式函数（useChat / useAutoRefresh）
│       └── router/index.js       # 路由 (/ → 聊天, /admin → 管理后台)
│
├── utils/                        # 工具函数
│   ├── config.py                 # 统一配置管理（多数据源/模型路由/行业本体）
│   ├── logger.py                 # 日志工具（分层/轮转/全链路追踪）
│   └── security.py               # 安全防护（SQL注入/XSS/输入净化）
│
├── tests/                        # 测试
│   ├── test_core.py              # 核心功能测试
│   ├── test_agents.py            # Agent协同层测试
│   ├── test_zhipu.py             # 智谱GLM API测试
│   └── test_xfyun.py             # 讯飞星火 API测试
│
├── data/                         # 运行时数据（已 gitignore）
├── logs/                         # 运行时日志（已 gitignore）
│
├── .env                          # 环境变量（已 gitignore）
├── .env.example                  # 环境变量模板（提交到仓库）
├── .gitignore                    # Git忽略规则
├── requirements.txt              # Python依赖
├── demo.py                       # 完整演示脚本
├── locustfile.py                 # Locust压力测试
├── start_frontend.py             # 一键启动脚本（后端 + Vite前端）
│
├── Dockerfile                    # 后端 Docker 构建
├── Dockerfile.frontend           # 前端 Docker 构建（Node构建 + Nginx运行）
├── docker-compose.yml            # 容器编排（backend + frontend + mysql + neo4j）
├── TEAM_GUIDE.md                 # 团队操作指南 ← 新成员必读
└── README.md                     # 项目说明（本文档）
```

---

## 三、大模型基座层

### 3.1 模型策略

采用 **"主力模型 + 备选模型"** 的双层策略：

| 模型定位 | 选用方案 | 部署方式 | 承担任务 | 选择理由 |
|---------|---------|---------|---------|---------|
| **主力模型** | 智谱 GLM-4 系列 | 云端API调用 | 综合推理、报告生成、复杂分析等高难度任务 | 中文能力出色、推理能力强、API价格有竞争力、国产模型合规性好 |
| **备选模型** | DeepSeek / 通义千问 / Kimi | 云端API调用 | 主力模型限流或故障时的降级备选 | 多提供商冗余，保证高可用性 |
| **降级策略** | 自动切换 | 自动检测 | 主力模型调用失败时自动切换至备选模型 | 保证服务连续性 |

### 3.2 支持的模型提供商

| 提供商 | 代表模型 | 认证方式 | 特性支持 |
|--------|---------|---------|---------|
| **智谱AI (Zhipu)** | `glm-4-flash`, `glm-4-air`, `glm-4`, `glm-4-plus`, `glm-4-long`, `glm-4-alltools` | Bearer Token | JSON模式、工具调用、流式输出 |
| **DeepSeek** | `deepseek-chat`, `deepseek-reasoner` | Bearer Token | 标准OpenAI兼容 |
| **通义千问 (DashScope)** | `qwen-turbo`, `qwen-plus`, `qwen-max` | Bearer Token | 标准OpenAI兼容 |
| **Kimi (Moonshot)** | `moonshot-v1-8k`, `moonshot-v1-32k`, `moonshot-v1-128k` | Bearer Token | 标准OpenAI兼容 |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` | Bearer Token | 标准OpenAI兼容 |
| **讯飞星火** | `generalv3.5`, `pro-128k`, `4.0Ultra` | HMAC-SHA256签名 | 国产模型 |

### 3.3 智谱GLM模型能力矩阵

| 模型 | JSON模式 | 工具调用 | 流式 | 适用场景 |
|------|----------|----------|------|---------|
| `glm-4-flash` | ✓ | ✗ | ✓ | 开发测试、低成本批量处理 |
| `glm-4-air` | ✓ | ✓ | ✓ | 生产环境日常问答 |
| `glm-4-airx` | ✓ | ✓ | ✓ | 高性能生产环境 |
| `glm-4` | ✓ | ✓ | ✓ | 高精度知识抽取 |
| `glm-4-plus` | ✓ | ✓ | ✓ | 最新旗舰，最强能力 |
| `glm-4-long` | ✓ | ✓ | ✓ | 长文本JD处理 |
| `glm-4-alltools` | ✓ | ✓ | ✓ | 需要工具调用/联网搜索 |

### 3.4 降级策略

```python
# 当主力模型返回 401/429/500/502 时，自动切换至智谱GLM
llm.get_status()  # 查看当前服务状态
# {
#   "provider": "zhipu",
#   "model": "glm-4-flash",
#   "fallback_active": false,
#   "fallback_reason": "",
#   "zhipu_configured": true
# }
```

---

## 四、Agent协同层

### 4.1 架构设计

采用 **"1个Master Agent + 5个专业子Agent"** 的多智能体协同架构。

```
用户自然语言提问
    ↓
Master Agent（总调度官）
    ├── 意图识别 → 八大意图分类
    ├── 任务分解 → 拆分为有序子任务
    └── 结果汇总 → 整合各Agent输出
        ↓
    ┌─────────┬─────────┬─────────┬─────────┬─────────┐
    ↓         ↓         ↓         ↓         ↓
岗位分析   差距分析   学习规划   趋势预测   报告生成
Agent      Agent      Agent      Agent      Agent
    ↓         ↓         ↓         ↓         ↓
    └─────────┴─────────┴─────────┴─────────┘
                        ↓
                   工具层（知识图谱 · RAG检索 · 数据库）
                        ↓
                   大模型基座（智谱GLM / DeepSeek / 通义千问）
```

### 4.2 Agent角色说明

| Agent | 角色定位 | 核心工作 | 关键输出 |
|-------|---------|---------|---------|
| **Master Agent** | 总调度官 | 意图识别、任务分解、结果汇总 | 结构化执行计划、综合回答 |
| **岗位分析Agent** | 行业研究员 | 调用知识图谱、RAG、数据库融合分析 | 必备/加分技能清单、薪资范围、学历经验要求、相似岗位推荐 |
| **差距分析Agent** | 能力评估师 | 用户技能映射到标准体系，逐项对比计算匹配度 | 匹配度评分、雷达图数据、关键差距排序、提升优先级建议 |
| **学习规划Agent** | 职业规划师 | 查询技能前置依赖确定学习顺序，检索学习资源 | 分阶段学习计划、推荐资源、里程碑检查点、路径可视化数据 |
| **趋势预测Agent** | 趋势分析师 | 基于时序统计数据和行业报告分析技能需求变化趋势 | 热门/新兴/衰退技能排行、未来趋势预测、职业发展建议 |
| **报告生成Agent** | 报告撰写人 | 整合各Agent分析结果，生成结构化综合报告 | Markdown格式报告（含摘要、分析、数据引用、建议） |

### 4.3 八大意图类别

| 意图类别 | 含义 | 用户提问示例 |
|---------|------|------------|
| 岗位能力分析 | 分析特定岗位的技能要求 | "Python后端开发需要什么技能？" |
| 能力差距分析 | 评估用户现有能力与目标岗位的差距 | "我会Java，想转数据分析，差什么？" |
| 学习路径规划 | 为用户制定技能提升路线 | "如何从前端转全栈开发？" |
| 趋势预测分析 | 分析行业或技能的发展趋势 | "AI行业未来什么技能最重要？" |
| 岗位对比分析 | 对比不同岗位的差异 | "前端和后端的技能要求有什么不同？" |
| 简历岗位匹配 | 评估简历与岗位的匹配度 | "我的简历适合投哪些岗位？" |
| 报告生成 | 生成综合分析报告 | "帮我出一份数据分析行业报告" |
| 通用问答 | 其他一般性问题 | "什么是微服务架构？" |

### 4.4 工作流编排

核心设计原则是 **按需调度、按序执行** —— 简单问题调用少量Agent快速响应，复杂问题自动编排多Agent深度分析。

| 场景 | 工作流 | Agent调用链路 |
|------|--------|-------------|
| 场景一：纯岗位分析 | `job_analysis` | Master → 岗位分析Agent → 输出 |
| 场景二：能力差距分析 | `skill_gap` | Master → 岗位分析Agent → 差距分析Agent → 输出 |
| 场景三：完整学习路径规划 | `learning_path` | Master → 岗位分析Agent → 差距分析Agent → 学习规划Agent → 输出 |
| 场景四：趋势分析 | `trend_analysis` | Master → 趋势预测Agent → 输出 |
| 场景五：综合报告生成 | `comprehensive_report` | Master → 岗位分析Agent ∥ 趋势预测Agent(并行) → 报告生成Agent → 输出 |

### 4.5 记忆管理系统

| 记忆类型 | 作用 | 存储方式 | 保留时长 |
|---------|------|---------|---------|
| 短期记忆 | 维持当前对话上下文连贯性 | 内存中的对话窗口 | 当前会话有效，保留最近10轮 |
| 长期记忆 | 持久化存储用户画像和历史分析结果 | Redis持久化存储 | 30天有效期 |

---

## 五、快速开始

### 5.1 环境准备

```bash
# 1. 克隆项目
cd llm_module

# 2. 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

### 5.2 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件，填入你的API Key
```

**推荐配置（智谱GLM为主力模型）：**

```env
# ========== 智谱AI (Zhipu) 主力配置 ==========
LLM_API_KEY=your_zhipu_api_key
LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-flash

# ========== 备选模型配置（可选） ==========
# DeepSeek
# LLM_API_KEY_ALT=your_deepseek_key
# LLM_API_BASE_ALT=https://api.deepseek.com/v1
# LLM_MODEL_ALT=deepseek-chat

# 讯飞星火（可选）
# XFYUN_APPID=your_appid
# XFYUN_APIKEY=your_apikey
# XFYUN_APISECRET=your_apisecret

# ========== 数据库配置 ==========
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=1
MYSQL_PASSWORD=root1234
MYSQL_DATABASE=job_competency

# ========== Neo4j 图数据库 ==========
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678

# ========== Elasticsearch ==========
ES_HOST=http://localhost:9200
ES_INDEX=job_competency

# ========== 向量数据库 ==========
VECTOR_DB_PATH=./data/vector_db

# ========== 服务配置 ==========
HOST=0.0.0.0
PORT=5173
DEBUG=true
```

### 5.3 启动服务

#### 方式一：Docker 一键启动（推荐）

```bash
# 启动后端 + MySQL + Neo4j
docker compose up -d --build backend
```

#### 方式二：本地 Python 直接运行

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 启动 FastAPI 服务
python -m api.main

# 或使用 uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 5173 --reload
```

#### 启动前端（Vue 开发模式）

```powershell
# 需先启动后端（方式一或方式二）
cd frontend
npm install        # 仅首次
npm run dev        # 热更新开发服务器 → http://localhost:5173
```

#### 一键启动（后端 + 前端）

```powershell
python start_frontend.py
# 自动安装前端依赖 → 启动后端 → 启动 Vite → 打开浏览器
```

服务启动后访问：
- 前端页面: `http://localhost:5173`
- API文档: `http://localhost:5173/docs`
- 健康检查: `http://localhost:5173/health`
- 管理后台: `http://localhost:5173/admin`
- Neo4j管理: `http://localhost:7474/browser/`

### 5.4 运行演示

```bash
# 完整演示（知识抽取、问答、图谱构建）
python demo.py

# 运行测试
python -m pytest tests/ -v
```

---

## 六、API接口

### 6.1 Agent协同层接口（/agents/*）

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /agents/chat` | 智能对话 | 意图识别→任务分解→执行→汇总，返回 `{answer, intent, tasks, session_id}` |
| `POST /agents/workflow/{type}` | 执行预定义工作流 | job_analysis / skill_gap / learning_path / trend_analysis / comprehensive_report |
| `GET /agents/model-status` | 当前模型状态 | 返回当前使用的提供商和模型名 |
| `GET /agents/intents` | 支持意图列表 | 8种意图类型及示例 |
| `GET /agents/workflows` | 支持工作流列表 | 5种工作流场景及Agent调用链 |
| `GET /agents/industries` | 支持行业列表 | IT/金融/医疗/制造/教育 |
| `GET /agents/roles` | 支持角色列表 | 求职者/HR/规划师/管理者 |
| `GET /agents/sessions` | 所有会话列表 | |
| `DELETE /agents/sessions/{id}` | 删除会话 | |

### 6.2 版本化 RESTful API（/api/v1/*）

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/sessions` | 创建会话 | 可指定行业/角色 |
| `GET /api/v1/sessions` | 会话列表 | |
| `GET /api/v1/sessions/{id}` | 会话详情 | 含消息数 |
| `DELETE /api/v1/sessions/{id}` | 删除会话 | |
| `POST /api/v1/sessions/{id}/chat` | 会话内对话 | 支持多轮上下文 |
| `GET /api/v1/sessions/{id}/chat/stream` | 流式对话(SSE) | 实时推送意图/任务/回答 |
| `GET /api/v1/sessions/{id}/messages` | 消息历史 | |
| `POST /api/v1/evaluations` | 提交评价 | 评分1-5 + 反馈文本 |

### 6.3 管理监控接口（/api/v1/admin/*）

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/admin/metrics` | 监控汇总 | 请求/Agent/LLM/意图/错误指标 |
| `GET /api/v1/admin/traces` | 最近追踪列表 | |
| `GET /api/v1/admin/traces/{id}` | 单条追踪详情 | 全链路时间线 |
| `GET /api/v1/admin/alerts` | 告警历史 | |
| `GET /api/v1/admin/metrics/prometheus` | Prometheus导出 | |

### 6.4 认证接口（/api/v1/auth/*）

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/auth/register` | 用户注册 | |
| `POST /api/v1/auth/login` | 用户登录 | 返回 JWT Token |
| `POST /api/v1/auth/refresh` | 刷新 Token | |
| `GET /api/v1/auth/me` | 当前用户信息 | 需认证 |

### 6.5 健康检查接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /health` | 基础检查 | |
| `GET /api/v1/health/live` | 存活检查 | 进程活着即返回 |
| `GET /api/v1/health/ready` | 就绪检查 | 数据库/LLM/Neo4j/向量库均可用 |
| `GET /api/v1/health/probe` | LLM探测 | 发送轻量请求验证API连通性 |

### 6.6 查询接口（/api/v1/*）

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/intents` | 意图列表（包装格式） | |
| `GET /api/v1/workflows` | 工作流列表 | |
| `GET /api/v1/industries` | 行业列表 | |
| `GET /api/v1/roles` | 角色列表 | |
| `GET /api/v1/tools` | 内置工具列表 | |
| `GET /api/v1/model-status` | 模型状态（包装格式） | |

### 6.7 使用示例

**Agent智能对话：**

```bash
curl -X POST http://localhost:5173/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Python后端开发需要什么技能？"
  }'
```

**执行工作流：**

```bash
curl -X POST http://localhost:5173/agents/workflow/skill_gap \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我会Java，想转数据分析，差什么？"
  }'
```

---

## 七、技术选型

| 技术组件 | 选用方案 | 选择理由 |
|---------|---------|---------|
| Web框架 | FastAPI | 原生异步支持、自动API文档生成、WebSocket内置支持 |
| 多Agent框架 | 自定义轻量实现 | 灵活可控、与现有架构无缝集成、无额外重依赖 |
| 主力大模型 | 智谱 GLM-4 系列 | 中文推理能力出色、API调用成本有竞争力、国产模型合规性好 |
| 备选模型 | DeepSeek / 通义千问 / Kimi | 多提供商冗余、保证高可用性 |
| 向量数据库 | ChromaDB | 开源轻量、支持持久化、与LangChain生态集成 |
| 图数据库 | Neo4j | 原生图存储、Cypher查询语言、可视化支持 |
| 关系数据库 | MySQL / SQLite | MySQL生产级、SQLite开发测试降级 |
| 搜索引擎 | Elasticsearch | 全文检索、分词支持、聚合分析 |
| 数据验证 | Pydantic v2 | 类型安全、自动校验、序列化支持 |
| HTTP客户端 | httpx | 异步支持、与asyncio深度集成 |
| 配置管理 | python-dotenv | 环境变量管理、开发/生产环境隔离 |

---

## 八、核心设计决策

### 8.1 大模型服务层

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 多提供商支持 | 6家提供商 | 避免单点故障，灵活切换 |
| 智谱专用路径 | 专用 `_chat_zhipu` | 特有错误码和模型特性需要专用处理 |
| 自动降级 | 错误码触发 | 401/429/500/502 自动切换备选 |
| JSON模式 | 模型支持检测 | 提升NER抽取准确率 |
| 流式处理 | 专用SSE解析 | 保持代码清晰，支持打字机效果 |

### 8.2 Agent协同层

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 自定义框架 | 不引入LangGraph | 轻量可控、与现有架构无缝集成 |
| 并行执行 | `asyncio.gather` | 无依赖Agent并行，提升响应速度 |
| 意图识别 | LLM-based分类 | 灵活、可扩展、支持复杂语义理解 |
| 工作流编排 | 预定义场景 | 覆盖80%用户需求，响应效率与分析深度自适应平衡 |

---

## 九、常见问题

### Q1: 如何选择主力模型？

推荐配置智谱GLM-4系列作为主力模型：
- 开发测试：`glm-4-flash`（免费、快速）
- 生产环境：`glm-4-air`（性价比高）
- 高精度任务：`glm-4` 或 `glm-4-plus`（最强能力）

### Q2: 降级策略如何工作？

当主力模型返回 401/429/500/502 错误时，系统自动切换至备选模型。可通过 `get_status()` 查看当前状态。

### Q3: 如何添加新的Agent？

1. 继承 `BaseAgent` 类，实现 `execute()` 方法
2. 在 `MasterAgent` 中注册新Agent
3. 在 `intent_agent_map` 中配置意图映射
4. 在 `decompose_task()` 中添加任务分解逻辑

### Q4: 如何扩展新的模型提供商？

1. 在 `_detect_provider()` 中添加URL检测规则
2. 添加专用的 `_chat_{provider}()` 方法
3. 在 `chat()` 中添加路由分支

---

## 十、开发团队

- **大模型集成**：智谱GLM-4系列多提供商兼容服务
- **Agent协同**：1+5多智能体协同架构
- **知识图谱**：Neo4j时序知识图谱构建
- **RAG检索**：ChromaDB向量检索增强

---

## 十一、许可证

本项目仅供学习和研究使用。

---

> **岗能智绘** —— 让岗位能力分析更智能、更精准、更有预见性。
