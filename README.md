# JobHunter

智能求职推荐平台 —— 聚合多源招聘信息，基于简历技能档案做 AI 推荐与可视化分析。

---

## 技术栈

| 模块 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite 5 + Pinia + Vue Router 4 + Element Plus + ECharts + axios |
| 后端 | FastAPI + Uvicorn + SQLAlchemy 2.0(async) + Pydantic v2 |
| 数据库 | MySQL 8 (aiomysql / PyMySQL) |
| LLM 简历解析 | 大模型可切换：智谱 glm-4-flash（默认）/ DeepSeek / Kimi / 通义（在 `llm_module/.env` 配置） |
| 向量检索 | ChromaDB（简历-JD 语义匹配 / 推荐系统） |
| 图数据库 | Neo4j（岗位方向知识图谱：方向画像 + 相似方向） |
| 检索 | Elasticsearch 8（职位全文检索） |
| 认证 | JWT (python-jose + passlib) |

---

## 仓库结构（单分支 main）

> **协作模式**：项目前后端曾按分支分离开发（frontend / backend / llm_model），
> 已全部合并进 `main`。**现在统一在 main 分支开发与提交**，克隆即得完整项目。

```
JobHunter/  (main 分支)
├── app/              后端 FastAPI(含 core/api/services/models)
├── db/               建表脚本 + 数据文件 + 文档(ES/爬虫/Schema)
├── docs/             开发文档
├── evaluation/       评测套件(简历解析/人岗匹配, 含测试简历与报告)
├── scripts/          同步/初始化脚本(ES/Neo4j/向量库/MySQL导入)
├── src/ index.html package.json   前端 Vue 3
├── llm_module/       LLM 简历解析服务(独立 FastAPI, 端口 8001)
└── requirements.txt run.py        后端依赖与入口
```

---

## 一、克隆代码

```bash
git clone https://github.com/Zzz-cy/JobHunter.git
# 得到 app/(后端) + src/(前端) + llm_module/(LLM模块) 的完整项目
```

---

## 二、后端启动

### 1. 环境要求

- Python 3.10+
- MySQL 8.x（需本地或远端可访问）
- Elasticsearch 8（职位全文检索用）
- Neo4j（知识图谱用，缺失时图谱页降级为演示数据，不影响其他功能）

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
| `JWT_SECRET_KEY` | 生产环境务必改成 32+ 字符随机串（LLM 引擎验签也用这个，两边要一致） |
| `ES_URL` / `ES_USERNAME` / `ES_PASSWORD` | Elasticsearch 连接信息 |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j 连接信息 |
| `ZHIPU_API_KEY` | 智谱 API Key（推荐的向量召回 + LLM 重排用） |
| `LLM_SERVICE_URL` | LLM 引擎地址（默认 `http://localhost:8001`） |

### 4. 初始化数据库

```bash
# 在 backend 目录下
python -m scripts.init_storage
```

该脚本会依次执行：

1. `db/mysql/01_schema.sql` —— 建表
2. `db/mysql/02_seed.sql` —— 字典 + 测试账号
3. `db/mysql/03_mock_data.sql` —— 假数据（前端联调用）

### 5. 初始化 ES 索引与 Neo4j 图谱（可选，用到对应功能再跑）

```bash
# ES: 建索引 + 同步职位数据(全文检索用)
python -m scripts.init_es_index
python -m scripts.sync_jobs_to_es

# Neo4j: 从 db/neo4j/jobs.json 建岗位方向知识图谱(会问两遍 Neo4j 密码)
python -m scripts.init_neo4j

# ChromaDB: 构建岗位向量库(推荐系统语义召回用)
python -m scripts.build_job_vectors
```

### 6. 验证连接

```bash
python -m scripts.check_db
```

输出 `✅ 全部通过` 即配置成功。

### 7. 启动服务

```bash
python run.py
```

默认监听 `http://127.0.0.1:8000`，API 文档：`http://127.0.0.1:8000/docs`。

> 端口/Host 在 `.env` 的 `APP_HOST` / `APP_PORT` 修改。

---

## 二·五、LLM 模块启动

简历 AI 解析服务（Python/FastAPI，独立于主后端），主后端通过 HTTP 调用它解析简历。

```bash
cd llm_module

# 依赖(与主后端一致装法)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 配置 .env(从 .env.example 复制, 填大模型 API Key)
# 默认主力: 智谱 glm-4-flash; 也可切换 DeepSeek/Kimi/通义(改 LLM_API_* 配置)

# 启动(端口 8001, 不要用 5173 以免和前端冲突)
python -m api.main
```

- 健康检查：`http://localhost:8001/health`
- 简历解析接口：`POST /agents/analyze-resume`（由主后端自动调用，无需手动请求）
- 主后端连接地址在 backend 的 `.env` 中配置：`LLM_SERVICE_URL=http://localhost:8001`

---

## 三、前端启动

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
| `/jobs` | 职位列表（ES 检索 + 多维筛选 + 分页） | 否 |
| `/jobs/:id` | 职位详情 | 否 |
| `/job-recommend` | 岗位推荐（技能召回 + 向量召回 + LLM 重排，带匹配分与理由） | 是 |
| `/resume` | 简历管理（上传 + AI 解析） | 是 |
| `/dashboard` | 数据分析大盘（ECharts，含技能需求演化时序图） | 否 |
| `/knowledge-graph` | 知识图谱（Neo4j 岗位方向画像，力导向图） | 否 |
| `/recommend` | AI 求职顾问（对话式，管理员可从此进 Agent 监控后台） | 是 |
| `/admin` | Agent 监控后台 | 管理员 |
| `/data-admin` | 数据管理 | 管理员 |
| `/profile` | 个人中心（求职进度看板） | 是 |
| `/login` `/register` | 登录 / 注册 | 否 |

### 准确率评测（可复现）

`backend/evaluation/` 内置评测套件：10 份合成简历 + 标准答案 + 自动化脚本。

```bash
# 需先启动主后端(8000) + LLM引擎(8001)
python evaluation/gen_resumes.py      # 生成测试简历(已内置, 一般不用重跑)
python evaluation/eval_parse.py       # 简历解析评测 → report_parse.md
python evaluation/eval_matching.py    # 人岗匹配评测 → report_matching.md
```

最近一次实测（16 份测试简历，含 6 份高难度样本）：简历解析综合字段准确率 **95.8%**，人岗匹配 M1 命中率 **90.6%**、Top1 相关率 **100%**。详见 `evaluation/report_parse.md` 与 `report_matching.md`。

### 后端 API

启动后访问 `http://127.0.0.1:8000/docs` 查看完整 Swagger 文档。

---

## 六、团队协作（单分支 main）

> 项目前期按 frontend / backend / llm_model 分支分离开发，现已全部合并进 `main`。
> **统一在 main 分支提交**，无需切分支、无需多目录。

### 提交信息规范

`<type>: <desc>`，例如 `feat: 新增职位搜索接口`、`fix: 修复登录态丢失`

| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 文档 |
| `refactor` | 重构 |
| `chore` | 杂项（依赖、配置等） |

### 日常开发流程（多人协作，单分支）

```bash
cd JobHunter    # 仓库根目录(改前端后端都在这里)

# 1. 开始干活前先拉最新
git pull

# 2. 写代码...(改文件)

# 3. 提交前再拉一次,避免和队友刚推的代码冲突
git pull

# 4. 看一眼要提交哪些文件(防止误传,尤其注意别把 .env/数据文件带进来)
git status

# 5. 确认无误后提交 + 推送
git add .
git commit -m "feat: 描述你改了啥"
git push
```

### 为什么要先拉再提交

队友可能在你写代码期间推了新代码。不拉就 push，会被拒绝（non-fast-forward）。
提前拉能尽早发现冲突，避免白干。单分支模式下这一点尤其重要——**所有人都在 main 上，冲突概率比分支模式高**，勤 pull 是最有效的预防。

### 常用场景

**只提交部分文件：**

```bash
git add app/api/users.py       # 只加这一个
git commit -m "fix: 修复用户接口"
git push
```

**看具体改动内容：**

```bash
git status          # 看哪些文件变了
git diff            # 看具体改了什么内容
```

**误传了想撤回（不丢代码）：**

```bash
git reset HEAD 文件名        # 撤销暂存
```

### 冲突处理

```bash
git pull
# Auto-merging xxx.py
# CONFLICT (content): Merge conflict in xxx.py
```

打开冲突文件，会看到：

```
<<<<<<< HEAD
你写的代码
=======
队友写的代码
>>>>>>> 同事的commit
```

三选一：
- 保留你的：删掉 `=======` 到 `>>>>>>>` 那段
- 保留队友的：删掉 `<<<<<<<` 到 `=======` 那段
- 合并两者：手动整合，删掉所有标记

然后：

```bash
git add .
git commit -m "merge: 合并xxx冲突"
git push
```

### 关于 `git add .`

会把当前目录下**所有变化**（新增、修改、删除）都加入暂存区。
`.gitignore` 里排除的文件（如 `node_modules`、`.env`、`__pycache__`）不会进。

⚠️ **危险场景**：你改了 A、B、C 三个文件但只想提交 A，用 `git add .` 会把 B、C 也带上。
建议每次 `add` 前先 `git status` 确认。
