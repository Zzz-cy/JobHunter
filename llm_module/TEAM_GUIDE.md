# 岗能智绘 — 团队协作操作指南

> 面向团队开发者的日常操作手册，涵盖环境搭建、开发流程、测试验证与常见问题。

---

## 一、环境要求

| 工具 | 版本要求 | 备注 |
|------|---------|------|
| Python | ≥ 3.11 | Docker 内为 3.11-slim |
| Node.js | ≥ 20 | 仅前端开发需要 |
| npm | ≥ 10 | 随 Node.js 一起安装 |
| Docker & Docker Compose | 最新稳定版 | 推荐使用 Docker Desktop |
| Git | 最新版 | |

---

## 二、首次运行（两步启动）

### 2.1 克隆与配置

```bash
# 克隆仓库
git clone <仓库地址>
cd llm_module

# 复制环境变量模板并填写自己的 API Key
cp .env.example .env
```

**必须填写的配置项：**

```env
# 智谱AI API Key（主力模型，必须）
ZHIPU_API_KEY=your_key_here

# MySQL 密码（保持与 docker-compose.yml 一致即可）
MYSQL_PASSWORD=root1234

# Neo4j 密码
NEO4J_PASSWORD=12345678
```

> ⚠️ **安全提醒**：`.env` 文件包含 API Key，已加入 `.gitignore`，不会提交到仓库。每位团队成员需要各自填写自己的 Key。

### 2.2 启动后端（Docker）

```bash
# 一键启动后端 + MySQL + Neo4j
docker compose up -d --build backend
```

等待约 30 秒，验证后端是否就绪：

```bash
# 健康检查
curl http://localhost:5173/health

# API 文档
# 浏览器打开 http://localhost:5173/docs

# Neo4j 管理界面
# 浏览器打开 http://localhost:7474/browser/  (账号: neo4j / 密码: job_competency_2024)
```

### 2.3 启动前端（Vite 开发服务器）

```powershell
# 进入前端目录
cd frontend

# 安装依赖（仅首次）
npm install

# 启动热更新开发服务器
npm run dev
```

浏览器打开 `http://localhost:3000` 即可看到聊天界面。

---

## 三、日常开发流程

### 后端开发

```bash
# 后端代码修改后，Docker 会自动热重载（--reload 已开启）
# 如果新增了 Python 依赖，需要重新构建镜像
docker compose up -d --build backend
```

**后端代码结构（只需关注这些目录）：**

| 目录 | 作用 | 开发频率 |
|------|------|---------|
| `api/` | FastAPI 路由（main.py + agent_routes.py + v1/） | 高 |
| `agents/` | Agent 调度器（agent_coordinator.py） | 中 |
| `services/` | 业务服务层 | 高 |
| `core/` | 核心逻辑（抽取/图谱/问答） | 中 |
| `models/` | 数据模型（schemas.py + prompts.py） | 低 |
| `utils/` | 配置/日志/安全工具 | 低 |

### 前端开发

```powershell
cd frontend
npm run dev        # 开发，热更新
npm run build      # 生产构建，输出到 dist/
```

**前端组件树（快速定位）：**

```
frontend/src/
├── views/              ← 页面级组件
│   ├── ChatView.vue    ← 聊天主页 (/)
│   └── AdminView.vue   ← 管理后台 (/admin)
├── components/
│   ├── chat/           ← 聊天相关组件（7个）
│   ├── admin/          ← 管理后台 Tab（7个）
│   └── common/         ← 通用组件（5个）
├── api/index.js        ← 所有 API 调用统一封装
├── composables/        ← 组合式函数（状态管理）
└── router/index.js     ← 路由配置
```

### 代码提交规范

```bash
git add .
git commit -m "类型: 简要描述"

# 类型参考：
# feat     — 新功能
# fix      — Bug 修复
# refactor — 重构
# style    — 样式/UI 修改
# docs     — 文档
# chore    — 构建/依赖/配置
```

---

## 四、项目架构速览

```
用户浏览器 (http://localhost:3000)
    │  Vue 3 + Vite (代理API到5173)
    ▼
FastAPI 后端 (http://localhost:5173)
    │
    ├── api/          ← RESTful + WebSocket
    ├── agents/       ← Master Agent → 5 个子 Agent
    ├── services/     ← LLM / RAG / Neo4j / MySQL / ES
    └── core/         ← 知识抽取 / 图谱构建 / 问答
          │
          ▼
    外部依赖 (Docker 容器)
    ├── MySQL 8.0      → 端口 3307（主机映射）
    ├── Neo4j 5        → 端口 7474(HTTP) / 7687(Bolt)
    └── ChromaDB       → 本地文件存储
          │
          ▼
    大模型 API（智谱 GLM-4 系列为主力）
```

### 端口占用一览

| 端口 | 服务 | 用途 |
|------|------|------|
| 5173 | FastAPI | 后端 API |
| 3000 | Vite | 前端开发服务器（热更新） |
| 8080 | Nginx | 前端生产构建（Docker） |
| 3307 | MySQL | 数据库（主机映射） |
| 7474 | Neo4j | 图数据库浏览器界面 |
| 7687 | Neo4j | 图数据库 Bolt 协议 |

---

## 五、测试

```bash
# 环境：确保后端 Docker 正在运行

# 运行所有测试
cd llm_module
python -m pytest tests/ -v

# 单独测试
python -m pytest tests/test_core.py -v
python -m pytest tests/test_agents.py -v

# API 单点测试（curl）
curl http://localhost:5173/agents/model-status
curl -X POST http://localhost:5173/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Python后端需要什么技能？"}'
```

---

## 六、常见问题

### Q1: 端口被占用怎么办？

```bash
# 查看端口占用
netstat -ano | findstr :5173
netstat -ano | findstr :3000

# 杀掉占用进程（用实际的 PID 替换 1234）
taskkill /F /PID 1234
```

### Q2: Docker 构建失败？

```bash
# 查看日志
docker compose logs backend

# 重建（不使用缓存）
docker compose build --no-cache backend
docker compose up -d --build backend
```

### Q3: `npm install` 报错？

```powershell
# 清空缓存重试
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Q4: 如何添加新的 API 端点？

1. 在 `api/v1/routes.py` 或 `api/agent_routes.py` 中添加路由
2. 如果是新功能，在 `services/` 目录中实现业务逻辑
3. 如果有新的请求/响应模型，在 `models/schemas.py` 中定义
4. 更新 `frontend/src/api/index.js` 添加对应的前端 API 调用
5. 在前端组件中调用

### Q5: 如何查看日志？

```bash
# 后端日志（Docker）
docker compose logs backend

# 前端日志（浏览器开发者工具 Console）
# F12 → Console
```

---

## 七、生产部署

```bash
# 构建前端
cd frontend
npm install && npm run build

# 启动所有服务
docker compose up -d --build

# 访问 http://localhost:8080   (Nginx 生产模式)
```

> 生产环境建议修改 `docker-compose.yml` 中的默认密码，并通过 GitHub Secrets 或 CI/CD 变量管理 API Key。
