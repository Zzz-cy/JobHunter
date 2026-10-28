# JobHunter 后端开发指南

> **给队友的快速上手文档**：读完这份，就能独立开发新功能。
> **技术栈**：FastAPI + SQLAlchemy 2.0 (async) + aiomysql + Pydantic v2
> **最后更新**：2026-07-28

---

## 目录

- [一、项目结构与分层](#一项目结构与分层)
- [二、环境准备（5 分钟跑起来）](#二环境准备5-分钟跑起来)
- [三、开发一个新功能的完整流程](#三开发一个新功能的完整流程)
- [四、数据库 / ORM 规范](#四数据库--orm-规范)
- [五、Schema 规范](#五schema-规范)
- [六、Service 规范](#六service-规范)
- [七、API 规范](#七api-规范)
- [八、统一返回与异常处理](#八统一返回与异常处理)
- [九、鉴权（登录态）](#九鉴权登录态)
- [十、已踩过的坑（必读）](#十已踩过的坑必读)
- [十一、命名规范速查](#十一命名规范速查)
- [十二、调试技巧](#十二调试技巧)

---

## 一、项目结构与分层

```
backend/
├── app/
│   ├── main.py              # 入口（路由挂载、异常处理、静态文件）
│   │
│   ├── core/                # 基础设施（不用改业务逻辑）
│   │   ├── config.py        #   配置（从 .env 读）
│   │   ├── database.py      #   异步引擎 + get_db 依赖
│   │   ├── exceptions.py    #   业务异常类
│   │   └── exception_handlers.py  # 全局异常 → 统一 Result
│   │
│   ├── models/              # ORM 模型（对应数据库表）
│   ├── schemas/             # Pydantic Schema（入参/出参）
│   ├── services/            # 业务逻辑 + 数据库操作（★主要写这里）
│   ├── api/                 # 路由层（薄，只做参数接收 + 调 service）
│   └── utils/               # 工具（JWT、密码哈希）
│
├── db/
│   ├── mysql/01_schema.sql  # 建表脚本
│   ├── mysql/02_seed.sql    # 字典数据
│   ├── mysql/03_mock_data.sql  # 测试数据
│   └── DATABASE_SCHEMA.md   # ★数据库字段说明（单一真相源）
│
├── docs/                    # 文档
├── uploads/                 # 上传文件（已 gitignore）
├── .env                     # 环境变量（已 gitignore，绝不提交）
└── requirements.txt
```

### 分层职责（★核心认知）

```
请求 → api（路由层）→ service（业务层）→ models（ORM）→ 数据库
       管协议         管业务逻辑          管数据结构
```

| 层 | 职责 | 禁止做的事 |
|---|---|---|
| **api** | 接收请求、参数校验、调 service、包装 Result | ❌ 不直接写 SQL/ORM 查询 |
| **service** | 业务逻辑、所有数据库操作 | ❌ 不返回 `Result`、不碰 HTTP |
| **models** | 表结构定义、关系 | ❌ 不写业务逻辑 |

**铁律**：**数据库操作只能出现在 service 里**。db 由 api 层用 `Depends(get_db)` 拿到，作为参数传给 service。

---

## 二、环境准备（5 分钟跑起来）

### 1. 装依赖

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配 .env

复制 `.env.example`（或问队友要）成 `.env`，填数据库密码：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=jobhunter
JWT_SECRET_KEY=随便一串字符
```

### 3. 初始化数据库

```bash
# 用 db/mysql/ 下的脚本依次执行
mysql -u root -p jobhunter < db/mysql/01_schema.sql
mysql -u root -p jobhunter < db/mysql/02_seed.sql
mysql -u root -p jobhunter < db/mysql/03_mock_data.sql
```

### 4. 启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 看接口文档。

---

## 三、开发一个新功能的完整流程

以"收藏职位"为例，**按这个顺序写**：

```
1. models/xxx.py        确认/修改表结构（对应字段）
2. schemas/xxx.py       定义入参 Schema + 出参 Schema
3. services/xxx_service.py  写业务逻辑 + 数据库操作
4. api/xxx.py           写路由（调 service，包装 Result）
5. api/__init__.py      注册路由到 routers 列表
6. DATABASE_SCHEMA.md   表结构有变就同步更新文档
```

**核心顺序**：**从数据层往上写**（model → schema → service → api），不要反过来。

---

## 四、数据库 / ORM 规范

### 1. 查询 API 速查（async SQLAlchemy 2.0）

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 查单个对象（按主键）
job = await db.scalar(select(Job).where(Job.id == 1))

# 查列表
result = await db.scalars(select(Job).where(Job.city == "北京"))
jobs = result.all()

# 聚合统计
from sqlalchemy import func
total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

# 新增
db.add(new_obj)
await db.commit()
await db.refresh(new_obj)   # 拿到自增 id 和默认值

# 更新（先查出来再改字段）
obj.field = new_value
await db.commit()
```

### 2. relationship 配 selectin 预加载

async 模式下，**所有会被序列化/访问的关系都要配 `lazy="selectin"`**，否则报 `MissingGreenlet`：

```python
# models/job.py
class Job(Base):
    company: Mapped["Company"] = relationship(back_populates="jobs", lazy="selectin")
    skills: Mapped[list["JobSkill"]] = relationship(..., lazy="selectin")
```

### 3. 跨 relationship 取值用 @property 桥接

Pydantic v2 的 `from_attributes` 模式**不能直接取嵌套关系属性**（如 `job_skill.skill.name`）。要在 ORM 模型上加 `@property`：

```python
# models/job.py 的 JobSkill
@property
def skill_name(self) -> str | None:
    return self.skill.name if self.skill else None
```

然后 schema 用普通字段 `skill_name: str | None = None` 就能取到。

### 4. 软删除 + 唯一键的坑

项目所有业务表带 `is_deleted`（软删除）。**唯一键不关心 is_deleted**，所以 upsert 时查询**不要过滤 is_deleted**，要能"复活"软删记录：

```python
# ✅ upsert 查询: 不加 is_deleted 过滤（要能复活）
app = await db.scalar(select(Application).where(
    Application.user_id == user_id,
    Application.job_id == job_id,
))
if app:
    app.is_deleted = 0   # 复活
    ...

# ✅ 只读查询: 要加 is_deleted == 0（只看有效数据）
jobs = await db.scalars(select(Job).where(Job.is_deleted == 0, ...))
```

---

## 五、Schema 规范

### 1. 继承基类

```python
from app.schemas.base import SchemaBase, ORMOut

class RegisterSchema(SchemaBase):  # 入参用 SchemaBase（严格）
    ...

class JobOut(ORMOut):              # 出参用 ORMOut（从 ORM 序列化）
    ...
```

### 2. 入参严格、出参宽松

- **入参**（继承 `SchemaBase`）：`extra="forbid"`，多余字段报错，防埋雷
- **出参**（继承 `ORMOut`）：`extra="ignore"`，只返回声明字段

### 3. 分页复用 PageParams

```python
from app.schemas.page import PageParams

class JobSearchSchema(PageParams, ORMOut):
    keyword: str | None = None
    # 自动拥有 page / page_size / offset
```

### 4. 安全白名单

```python
class UserUpdateSchema(SchemaBase):
    nickname: str | None = None
    # ❌ 绝不声明 role / password_hash / is_deleted
    # 前端传了也会被 extra="forbid" 拦截，防越权
```

---

## 六、Service 规范

### 1. 命名：动作导向

```python
async def search_jobs(db, params, offset, limit) -> tuple[list, int]:  # ✅ 查
async def create_resume(db, ...):                                        # ✅ 增
async def favorite_job(db, job_id, user_id):                             # ✅ 业务动作
async def is_job_active(db, job_id) -> bool:                             # ✅ 判断
```

### 2. 返回纯数据，不返回 Result

```python
# ✅ 正确：返回数据，让 api 层包装
async def search_jobs(...) -> tuple[list[Job], int]:
    return jobs, total

# ❌ 错误：service 不该知道 Result
async def search_jobs(...) -> Result:
    return Result.success(...)
```

### 3. db 作为参数传入，不自己 Depends

```python
# ✅ 正确：db 由 api 传入
async def favorite_job(job_id, db, user_id): ...

# ❌ 错误：service 不该用 Depends（那是 FastAPI 的东西）
async def favorite_job(job_id, db=Depends(get_db)): ...
```

---

## 七、API 规范

### 1. 路由注册

新路由模块要加到 `app/api/__init__.py` 的 `routers` 列表：

```python
# app/api/__init__.py
from app.api.xxx import router as xxx_router
routers = [auth_router, jobs_router, resumes_router, xxx_router]
```

### 2. 路由顺序：固定路径在前，动态路径在后

```python
# ✅ 正确顺序
@router.get("/page")              # 固定路径，先匹配
@router.get("/{id}")              # 动态路径，后兜底

# ❌ 错误顺序（/page 会被 /{id} 抢匹配）
@router.get("/{id}")
@router.get("/page")
```

### 3. 路径变量名必须合法且和参数一致

```python
# ✅ 合法：纯字母数字下划线，且路径名 = 参数名
@router.get("/{job_id}/similar")
async def similar(job_id: int): ...

# ❌ 非法：不能含 . 或 -
@router.get("/{job.id}/similar")    # 解析失败 → 404
```

### 4. RESTful 风格

| 操作 | 方法 | 示例 |
|---|---|---|
| 列表 | GET | `GET /jobs/page` |
| 详情 | GET | `GET /jobs/{id}` |
| 创建 | POST | `POST /jobs` |
| 更新 | PUT | `PUT /jobs/{id}` |
| 动作 | POST | `POST /jobs/{id}/favorite` |
| 删除 | DELETE | `DELETE /jobs/{id}/favorite` |

### 5. 序列化 schema 和 response_model 必须一致

```python
# ✅ 一致
@router.get("/{id}", response_model=Result[JobDetailOut])
async def get_job(id):
    return Result.success(data=JobDetailOut.model_validate(job))

# ❌ 不一致（声明 A 用 B 序列化，数据会丢）
@router.get("/{id}", response_model=Result[JobDetailOut])
async def get_job(id):
    return Result.success(data=JobOut.model_validate(job))  # 用了 JobOut!
```

---

## 八、统一返回与异常处理

### 1. 统一返回结构 Result

```python
from app.schemas import Result

# 成功
return Result.success(data=out)
return Result.success(message="已收藏")           # 无 data
return Result.success_page(page_result)            # 分页专用

# 业务失败：抛异常，不要自己返回 Result.fail
raise NotFoundError("职位不存在")
raise ParamError("参数错误")
```

### 2. 业务错误用异常抛，不要返回 Result.fail

项目有全局异常处理器，**所有业务错误用 `raise`**，会被自动转成统一 Result：

```python
from app.core.exceptions import NotFoundError, ParamError, ConflictError

# ✅ 正确：raise
if job is None:
    raise NotFoundError("职位不存在")

# ❌ 错误：service 里返回 fail
return Result.fail("职位不存在")
```

异常类对照：

| 异常类 | 业务码 | 场景 |
|---|---|---|
| `ParamError` | 100 | 参数校验/业务校验不过 |
| `UnauthorizedError` | 101 | 未登录 |
| `ForbiddenError` | 102 | 无权限 |
| `NotFoundError` | 103 | 资源不存在 |
| `ConflictError` | 104 | 冲突（如手机号已注册） |

---

## 九、鉴权（登录态）

### 1. 整个路由都要登录

```python
router = APIRouter(
    prefix="/resumes",
    dependencies=[Depends(get_current_user)],  # 所有接口都要登录
)
```

### 2. 单个接口要登录 + 拿当前用户

```python
from app.utils.jwtUtil import get_current_user

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),   # 拿到当前用户对象
):
    await save_resume(file, current_user.id, db)
```

### 3. Swagger 测试鉴权接口

1. 调 `POST /auth/login` 拿 token
2. 点页面右上角 🔒 Authorize，填 `Bearer <token>`
3. 再调鉴权接口

---

## 十、已踩过的坑（必读）

### 坑 1：async 函数忘 await → 静默失败

```python
# ❌ register 是 async，忘 await，异常永远抛不出
register(payload, db)

# ✅
await register(payload, db)
```

### 坑 2：漏 selectin → MissingGreenlet

async 下访问懒加载关系会报 `MissingGreenlet`。**所有要序列化的关系都配 `lazy="selectin"`**。

### 坑 3：路由顺序 → 固定路径被动态路径抢匹配

固定路径（`/page`、`/industries`）必须声明在动态路径（`/{id}`）**之前**。

### 坑 4：路径变量名非法（含 `.`）

`{job.id}` 非法，路由注册失败 → 404。用 `{job_id}`。

### 坑 5：`db.execute` 返回 Result，不是 ORM 对象

```python
# ❌ 把 Result 当 Job 用
job = await db.execute(select(Job).where(Job.id == 1))
job.title  # 报错

# ✅ 用 scalar 拿单个对象
job = await db.scalar(select(Job).where(Job.id == 1))
```

### 坑 6：软删除 + 唯一键冲突

upsert 时查询**不过滤 is_deleted**，要能复活软删记录（见第四章第 4 节）。

### 坑 7：序列化和 response_model 不一致

`model_validate` 用的 schema 必须和 `response_model` 一致，否则数据被砍。

---

## 十一、命名规范速查

| 对象 | 规范 | 示例 |
|---|---|---|
| 文件 | 资源名小写，api 用单数、service 加 `_service` | `jobs.py` / `jobs_service.py` |
| 模型类 | PascalCase，单数 | `class Job` |
| 表名 | snake_case，可复数 | `__tablename__ = "jobs"` |
| 字段 | snake_case | `salary_min` |
| API 函数 | 动词+资源（接口视角） | `get_job_page` |
| Service 函数 | 动作（系统视角） | `search_jobs` |
| Schema 入参 | `XxxSchema` / `XxxCreateSchema` | `JobSearchSchema` |
| Schema 出参 | `XxxOut`（列表）/ `XxxDetailOut`（详情） | `JobOut` / `JobDetailOut` |

---

## 十二、调试技巧

### 1. Swagger 测接口

http://localhost:8000/docs —— 不用写代码，可视化测试。

### 2. 万能测试脚本

`backend/test_query.py`（已 gitignore），改 `test()` 函数测任意 service/ORM：

```bash
cd backend && python test_query.py
```

### 3. 开 SQL 日志

`.env` 里 `MYSQL_ECHO=True`，控制台打印所有 SQL，排查查询问题。

### 4. 看原始数据

用 DBeaver / Navicat 直连 MySQL，写 SQL 验证数据真存进去了。

---

## 附：参考资料

- 数据库字段说明：`backend/db/DATABASE_SCHEMA.md`（单一真相源，改表必同步）
- 知识图谱方案：`backend/docs/KNOWLEDGE_GRAPH.md`
- 岗位推荐方案（简历→岗位匹配，技能+向量+LLM重排）：`backend/docs/RECOMMEND_SYSTEM.md`
- 统一返回结构：`app/schemas/result.py`
- 异常类：`app/core/exceptions.py`

---

**有问题随时问，别硬啃。**
