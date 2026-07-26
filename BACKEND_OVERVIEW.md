# JobHunter 后端项目结构

> FastAPI + SQLAlchemy 2.0(异步) + MySQL + Elasticsearch。
> 本文件只讲"目录怎么组织、各层职责、加新功能往哪写",配合 `db/` 下的 `DATABASE_SCHEMA.md` / `CRAWL_REQUIREMENTS.md` 阅读。

---

## 一、目录结构

```
backend/
├── app/                        # 应用主包, 所有代码在这
│   ├── main.py                 # 入口: 创建 FastAPI app, 挂路由/异常处理器/生命周期
│   │
│   ├── core/                   # 基础设施(跟业务无关)
│   │   ├── config.py           # 配置: 读 .env, 暴露 settings
│   │   ├── database.py         # 数据库: engine + AsyncSessionLocal + get_db 依赖
│   │   ├── exceptions.py       # 业务异常: BizException + 各具体异常(NotFoundError...)
│   │   └── exception_handlers.py  # 全局异常处理: 把异常转成统一 Result 格式
│   │
│   ├── models/                 # ORM 模型(SQLAlchemy, 对应数据库表)
│   │   ├── base.py             # 模型基类: Base / BigIntPk / 时间戳 mixin / 软删除 mixin
│   │   ├── user.py             # users 表
│   │   ├── resume.py           # resumes / resume_skills / resume_experiences / ...
│   │   ├── job.py              # jobs / job_skills
│   │   ├── company.py          # companies
│   │   ├── behavior.py         # applications / recommendations / chat_history
│   │   ├── dict.py             # skills / industries(字典表)
│   │   └── crawl.py            # crawl_sources / crawl_tasks
│   │
│   ├── schemas/                # Pydantic Schema(请求/响应数据形状)
│   │   ├── base.py             # 基类: SchemaBase(入参, 严格) / ORMOut(出参, 宽松)
│   │   ├── result.py           # 统一返回壳 Result[T] + 业务码 BizCode
│   │   ├── page.py             # 分页入参/出参
│   │   ├── auth.py             # 注册/登录入参出参
│   │   ├── user.py / jobs.py / resumes.py   # 各业务模块入参出参
│   │
│   ├── api/                    # 路由层(接口入口, 只做参数接收 + 调 service + 返回)
│   │   ├── __init__.py         # 聚合所有 router 到 routers 列表
│   │   ├── auth.py             # /auth 注册/登录
│   │   ├── user.py             # /users
│   │   ├── jobs.py             # /jobs
│   │   └── resumes.py          # /resumes(上传/列表/下载)
│   │
│   ├── services/               # 业务逻辑层(真正干活的地方)
│   │   ├── auth_service.py     # 注册/登录/生成 token
│   │   ├── user_service.py
│   │   ├── jobs_service.py
│   │   └── resumes_service.py  # 文件校验/落盘/建记录
│   │
│   └── utils/                  # 工具(跨业务复用)
│       ├── jwtUtil.py          # JWT 签发/解析 + get_current_user 依赖
│       └── pwdUtil.py          # bcrypt 密码哈希/校验
│
├── db/                         # 数据库相关(文档 + SQL)
│   ├── mysql/                 # 建表/种子/模拟数据 SQL
│   ├── DATABASE_SCHEMA.md     # 数据库表结构文档
│   ├── CRAWL_REQUIREMENTS.md  # 爬虫需求文档
│   └── ES_INDICES.md          # ES 索引文档
│
├── uploads/                   # 上传文件根目录(.gitignore 忽略)
├── .env                       # 环境变量(密钥/数据库密码, .gitignore 忽略)
└── requirements.txt           # Python 依赖
```

---

## 二、三层架构

每个接口的代码分三层,**职责严格分开**:

```
HTTP 请求
    ↓
[ api/ ]      接口入口: 接收参数(File/Form/Query) + 鉴权依赖 + 调 service + 返回 Result
    ↓
[ services/ ] 业务逻辑: 校验/组合/事务/调三方, 真正干活的地方
    ↓
[ models/ ]   ORM 模型: 定义表结构, 提供查询(select/where)
    ↓
MySQL / ES
```

**铁律**:api 层不写业务逻辑,service 层不直接处理 HTTP。这样接口能复用、好测试。

---

## 三、加一个新功能的标准流程

以"加个收藏接口 `POST /jobs/{id}/favorite`"为例:

| 步骤 | 文件 | 干啥 |
|---|---|---|
| 1 | `models/` | 如果涉及新表,定义 ORM 模型 |
| 2 | `schemas/jobs.py` | 定义入参/出参 Schema |
| 3 | `services/jobs_service.py` | 写业务函数,比如 `toggle_favorite(db, user_id, job_id)` |
| 4 | `api/jobs.py` | 加路由,接收参数 + 调 service + `return Result.success(...)` |

---

## 四、统一返回 & 业务码

**所有接口返回同一个壳**(前端只判断 `code`):

```json
{
  "code": 0,           // 0=成功, 非 0=业务错误
  "message": "ok",     // 给前端展示的提示
  "data": {...}        // 业务数据, 失败时为 null
}
```

- HTTP 状态码恒为 200(除 401/403/422 这种框架层的)
- 业务码定义在 `schemas/result.py` 的 `BizCode`(0 成功,1xx 通用,2xx 用户,3xx 职位...)
- 路由里直接 `return Result.success(data)` 或 `Result.fail(message, code)`

---

## 五、鉴权机制

- 登录成功后,`auth_service` 签发 JWT,载荷 `sub` 字段存 `user_code`
- 需要登录的接口,参数加 `current_user = Depends(get_current_user)`(`utils/jwtUtil.py`)
- `get_current_user` 会从 `Authorization: Bearer <token>` 提取并解析 token,返回 User 对象
- token 无效/过期统一抛 401

---

## 六、启动 & 调试

```bash
# 1. 装依赖
cd backend
pip install -r requirements.txt

# 2. 配环境变量(复制 .env.example 改名 .env, 填数据库密码/JWT 密钥等)

# 3. 建库(执行 db/mysql/ 下的 SQL)

# 4. 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问:
- Swagger 文档(可在线测接口): http://localhost:8000/docs
- ReDoc 文档(更适合阅读): http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 七、关键约定(避免踩坑)

1. **代码注释用中文**,跟现有风格一致(看 `main.py` / `services/` 就能感受到)
2. **入参严格 / 出参宽松**:入参 Schema 继承 `SchemaBase`(extra=forbid),出参继承 `ORMOut`(extra=ignore)
3. **新增路由模块只改 2 个文件**:`api/xxx.py` 定义 router + `api/__init__.py` 加进 routers 列表,`main.py` 不用动
4. **数据库迁移**:目前没有 Alembic,改表结构直接改 `db/mysql/01_schema.sql` + 手动 `ALTER TABLE`
5. **敏感配置走 .env**:密钥、数据库密码绝不硬编码,统一从 `settings` 读
6. **文件上传走 `uploads/`**:目录已被 `.gitignore` 忽略,不会进 git
