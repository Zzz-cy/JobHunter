# JobHunter

智能求职推荐平台 —— 聚合多源招聘信息，基于简历技能档案做 AI 推荐与可视化分析。

---

## 技术栈

| 模块 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite 5 + Pinia + Vue Router 4 + Element Plus + ECharts + axios |
| 后端 | FastAPI + Uvicorn + SQLAlchemy 2.0(async) + Pydantic v2 |
| 数据库 | MySQL 8 (aiomysql / PyMySQL) |
| 检索 | Elasticsearch 8 (后续启用) |
| 图数据库 | Neo4j (后续启用) |
| AI | 讯飞星火 (后续启用) |
| 认证 | JWT (python-jose + passlib) |

---

## 仓库结构（按分支拆分）

| 分支 | 内容 |
|---|---|
| `main` | 项目说明（仅 `README.md`） |
| `frontend` | 前端代码 |
| `backend` | 后端代码 |

> 本仓库按分支隔离前后端，`main` 只放项目总览文档。**本地开发需要分别拉取 `frontend` 和 `backend` 两个分支**。

---

## 一、克隆代码

前后端在不同分支，推荐用 `git worktree` 在本地拼出并列目录。

### 方案 A：git worktree（推荐）

```bash
# 1. 克隆 frontend 分支
git clone -b frontend https://github.com/Zzz-cy/JobHunter.git JobHunter-frontend
cd JobHunter-frontend

# 2. 把 backend 分支检出到同级目录
git worktree add ../JobHunter-backend backend
```

最终目录结构（两个目录并列）：

```
JobHunter-frontend/   # frontend 分支
└── (前端文件)
JobHunter-backend/    # backend 分支
└── (后端文件)
```

### 方案 B：分别克隆到两个目录

```bash
git clone -b frontend https://github.com/Zzz-cy/JobHunter.git JobHunter-frontend
git clone -b backend  https://github.com/Zzz-cy/JobHunter.git JobHunter-backend
```

### 方案 C：只看某一端

```bash
git clone -b frontend https://github.com/Zzz-cy/JobHunter.git  # 只要前端
git clone -b backend  https://github.com/Zzz-cy/JobHunter.git  # 只要后端
```

### 方案 D：只要项目说明

```bash
git clone -b main https://github.com/Zzz-cy/JobHunter.git
```

---

## 二、后端启动（backend 分支）

### 1. 环境要求

- Python 3.10+
- MySQL 8.x（需本地或远端可访问）
- (可选) Elasticsearch 8、Neo4j —— 后续模块才需要

### 2. 安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env            # Windows 用: copy .env.example .env
```

打开 `.env`，按本机实际情况修改：

| 关键变量 | 说明 |
|---|---|
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` | MySQL 连接信息 |
| `MYSQL_DATABASE` | 数据库名（默认 `jobhunter`，需先手动创建空库或由 init 脚本创建） |
| `JWT_SECRET_KEY` | 生产环境务必改成 32+ 字符随机串 |
| `ES_*` / `NEO4J_*` / `SPARK_*` | 后续模块启用时再填，暂可留空 |

### 4. 初始化数据库

```bash
# 在 backend 目录下
python -m scripts.init_storage
```

该脚本会依次执行：

1. `db/mysql/01_schema.sql` —— 建表
2. `db/mysql/02_seed.sql` —— 字典 + 测试账号
3. `db/mysql/03_mock_data.sql` —— 假数据（前端联调用）

### 5. 验证连接

```bash
python -m scripts.check_db
```

输出 `✅ 全部通过` 即配置成功。

### 6. 启动服务

```bash
python run.py
```

默认监听 `http://127.0.0.1:8000`，API 文档：`http://127.0.0.1:8000/docs`。

> 端口/Host 在 `.env` 的 `APP_HOST` / `APP_PORT` 修改。

---

## 三、前端启动（frontend 分支）

### 1. 环境要求

- Node.js 18+（推荐 20 LTS）
- npm / pnpm / yarn 任选

### 2. 安装依赖

```bash
cd frontend
npm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

默认 `http://localhost:5173`，会自动打开浏览器。

### 4. 与后端联调

`vite.config.js` 已配置代理：所有 `/api/*` 请求转发到 `http://127.0.0.1:8000`（去掉 `/api` 前缀）。

- **后端必须先启动**，否则前端所有接口请求会失败
- 若后端端口非 8000，需同步修改 `vite.config.js` 中的 `server.proxy.target`

### 5. 构建

```bash
npm run build       # 输出到 dist/
npm run preview     # 本地预览构建产物
```

---

## 四、常见问题

**Q：`git push` 报 `ssh: connect to host github.com port 22: Connection refused`**

22 端口被封，改用 HTTPS：

```bash
git remote set-url origin https://github.com/Zzz-cy/JobHunter.git
```

**Q：HTTPS 推送报 `SSL certificate ... unable to get local issuer certificate`**

Windows 上 OpenSSL 证书问题，改用 schannel：

```bash
git config --global http.sslBackend schannel
```

**Q：前端启动后接口全部 404 / 跨域**

确认后端已启动且端口是 8000；若改过端口，同步改 `vite.config.js`。

**Q：`init_storage` 报 Access denied**

`.env` 里的 `MYSQL_USER` / `MYSQL_PASSWORD` 不对，或该账号没有 `CREATE` 权限。

---

## 五、页面/接口速览

### 前端路由

| 路由 | 页面 | 需登录 |
|---|---|---|
| `/home` | 首页（搜索 + 热门） | 否 |
| `/jobs` | 职位列表（多维筛选 + 分页） | 否 |
| `/jobs/:id` | 职位详情 | 否 |
| `/recommend` | 智能推荐（匹配度评分） | 是 |
| `/resume` | 简历管理（上传 + 解析） | 是 |
| `/dashboard` | 数据分析大盘（ECharts） | 否 |
| `/profile` | 个人中心（求职进度看板） | 是 |
| `/login` `/register` | 登录 / 注册 | 否 |

### 后端 API

启动后访问 `http://127.0.0.1:8000/docs` 查看完整 Swagger 文档。

---

## 六、分支与协作

- `main`：项目总览（仅 README.md）
- `frontend`：前端代码
- `backend`：后端代码
- 提交信息建议：`<type>: <desc>`，例如 `feat: 新增职位搜索接口`、`fix: 修复登录态丢失`
