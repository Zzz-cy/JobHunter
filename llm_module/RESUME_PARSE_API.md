# 简历智能解析功能 — 技术文档

> **功能概述**：用户上传 PDF 或图片简历，系统自动提取文本，经 LLM 结构化抽取后返回对齐 `DATABASE_SCHEMA.md` 的标准字段。
> **对应表**：`resumes`（主表） + `resume_skills` + `resume_experiences` + `resume_educations`（子表）

---

## 一、架构总览

```
用户上传 PDF / 图片
        │
        ▼
┌──────────────────────────────────────────┐
│  api/agent_routes.py                     │
│  POST /agents/analyze-resume            │
│  POST /agents/analyze-resume-and-save   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  core/resume_parser.py                   │
│                                          │
│  第一段：文件 → 文本                      │
│    extract_resume_text()                 │
│    ├─ PDF: pdfplumber → PyMuPDF → OCR   │
│    └─ 图片: pytesseract OCR             │
│                                          │
│  第二段：文本 → 结构化 JSON               │
│    parse_resume_with_llm()              │
│    ├─ RESUME_PARSE_PROMPT 模板          │
│    ├─ LLM 调用 (JSON mode)              │
│    └─ _safe_json_parse + _normalize     │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  返回结构化 JSON（对齐 DATABASE_SCHEMA）  │
│  或写入数据库（-and-save 端点）           │
└──────────────────────────────────────────┘
```

---

## 二、API 接口

### 2.1 `POST /agents/analyze-resume`

**职责**：只抽取返回结构化字段，**不写库**。由调用方（JobHunter）负责归一化与入库。

#### 调用方式（三选一）

| 方式 | Content-Type | 参数 | 示例 |
|------|-------------|------|------|
| **上传文件** | `multipart/form-data` | `file` (UploadFile) | `curl -F "file=@resume.pdf" ...` |
| **表单传路径** | `multipart/form-data` | `file_url` + `file_type` (可选) | `curl -F "file_url=/path/to/resume.pdf" ...` |
| **JSON 传路径** | `application/json` | `{"file_url":"...", "file_type":"pdf"}` | `curl -H "Content-Type: application/json" -d '{"file_url":"..."}' ...` |

> `file_type` 不传时按扩展名自动推断：`.pdf` → pdf；`.png/.jpg/.jpeg/.webp/.bmp` → image。

#### 请求示例

```bash
# 方式1：上传文件（推荐）
curl -X POST http://localhost:8001/agents/analyze-resume \
  -F "file=@resume.pdf"

# 方式2：表单传本地路径
curl -X POST http://localhost:8001/agents/analyze-resume \
  -F "file_url=data/uploads/resumes/resume.pdf" \
  -F "file_type=pdf"

# 方式3：JSON body
curl -X POST http://localhost:8001/agents/analyze-resume \
  -H "Content-Type: application/json" \
  -d '{"file_url":"data/uploads/resumes/resume.pdf","file_type":"pdf"}'
```

#### 响应格式

**HTTP 始终返回 200**，业务成败看 `code` 字段：

```json
{
  "code": 0,
  "message": "解析成功",
  "data": {
    "name": "张三",
    "gender": 0,
    "age": 28,
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "city": "北京",
    "work_years": 5,
    "education": "本科",
    "expect_salary_min": 20000,
    "expect_salary_max": 30000,
    "expect_city": "北京",
    "expect_job": "高级Python开发工程师",
    "skills": ["Python", "Java", "Docker", "MySQL", "Vue"],
    "experiences": [
      {
        "company_name": "字节跳动",
        "title": "后端工程师",
        "start_date": "2022-06-01",
        "end_date": "2024-08-01",
        "description": "负责抖音电商后端订单系统",
        "is_current": 0
      }
    ],
    "educations": [
      {
        "school": "浙江大学",
        "major": "计算机科学与技术",
        "degree": "本科",
        "start_date": "2018-09-01",
        "end_date": "2022-06-01"
      }
    ],
    "parsed_raw": { "...LLM原始返回，调试用..." }
  },
  "request_id": "",
  "timestamp": "2026-07-29T17:17:59.245107"
}
```

#### 错误响应

```json
{
  "code": 400,
  "message": "不支持的文件类型: .txt",
  "data": null,
  "request_id": "",
  "timestamp": "..."
}
```

| 场景 | code | message |
|------|------|---------|
| 解析成功 | 0 | 解析成功 |
| 未提供文件 | 400 | 未提供文件：请上传文件(file)或传 file_url |
| 不支持的文件类型 | 400 | 不支持的文件类型: .xxx |
| 文件不存在 | 500 | 文件不存在或无法读取 |
| 简历内容为空 | 500 | 简历内容为空 |
| LLM 调用失败 | 500 | 简历分析服务异常 |
| LLM 返回非法 JSON | 500 | 简历分析服务异常 |

---

### 2.2 `POST /agents/analyze-resume-and-save`

**职责**：解析 + 一站式入库。用于本地联调验证，生产环境可下线。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | int (Form) | 是 | 所属用户 ID |
| `file` | UploadFile | 是 | 简历文件 |

```bash
curl -X POST http://localhost:8001/agents/analyze-resume-and-save \
  -F "user_id=1" \
  -F "file=@resume.pdf"
```

#### 响应示例

```json
{
  "code": 0,
  "message": "解析并入库成功",
  "data": {
    "resume_id": 3,
    "skill_count": 5,
    "experience_count": 1,
    "education_count": 1,
    "parsed": { "...同 analyze-resume 的 data ..." }
  }
}
```

#### 入库逻辑

| 步骤 | 目标表 | 说明 |
|------|--------|------|
| 3.1 | `resumes` | 写入主表（name/age/city/work_years/education/expect_* 等），`parse_status="done"` |
| 3.2 | `resume_skills` | 技能名先查 `skills` 字典匹配 `skill_id`，不存在则新建字典项再关联 |
| 3.3 | `resume_experiences` | 工作经历直接写入 |
| 3.4 | `resume_educations` | 教育经历直接写入 |

---

## 三、响应字段 ↔ 数据库映射

### 3.1 resumes 主表

| 接口返回字段 | 数据库列 | 类型 | 说明 |
|------------|---------|------|------|
| name | name | VARCHAR(64) | 姓名 |
| gender | gender | TINYINT | 0=男 1=女 |
| age | age | INT | 年龄 |
| phone | phone | VARCHAR(20) | 联系方式 |
| email | email | VARCHAR(128) | 邮箱 |
| city | city | VARCHAR(64) | 现居城市 |
| work_years | work_years | INT | 工作年限 |
| education | education | VARCHAR(16) | 最高学历 |
| expect_salary_min | expect_salary_min | INT | 期望薪资下限（元/月） |
| expect_salary_max | expect_salary_max | INT | 期望薪资上限（元/月） |
| expect_city | expect_city | VARCHAR(64) | 期望工作城市 |
| expect_job | expect_job | VARCHAR(128) | 期望岗位 |
| parsed_raw | parsed_raw | JSON | LLM 原始返回（调试用） |
| — | parse_status | VARCHAR(16) | 由入库方置 `done`/`failed` |
| — | parse_error | VARCHAR(512) | 失败时由入库方记录 |

### 3.2 resume_skills 关联表

| 接口返回字段 | 数据库列 | 说明 |
|------------|---------|------|
| skills[] 中的每个名称 | skill_id (经字典匹配) | 已存在→关联；不存在→新建字典项再关联 |
| — | proficiency | 默认 3（1-5） |

### 3.3 resume_experiences 子表

| 接口返回字段 | 数据库列 | 类型 |
|------------|---------|------|
| company_name | company_name | VARCHAR(128) |
| title | title | VARCHAR(128) |
| start_date | start_date | DATE |
| end_date | end_date | DATE |
| description | description | TEXT |
| is_current | is_current | TINYINT(1) |

### 3.4 resume_educations 子表

| 接口返回字段 | 数据库列 | 类型 |
|------------|---------|------|
| school | school | VARCHAR(128) |
| major | major | VARCHAR(128) |
| degree | degree | VARCHAR(32) |
| start_date | start_date | DATE |
| end_date | end_date | DATE |

---

## 四、核心模块详解

### 4.1 `core/resume_parser.py` — 两段式解析

#### 第一段：文件 → 文本（`extract_resume_text`）

**PDF 提取降级链**：

```
pdfplumber（主力）
    │ 失败 / 无文字
    ▼
PyMuPDF / fitz（兜底）
    │ 仍无文字（扫描件）
    ▼
PyMuPDF 渲染图片 → pytesseract OCR
```

| 步骤 | 库 | 说明 |
|------|---|------|
| 1 | `pdfplumber` | 对文字型 PDF 效果最好，中英文均支持 |
| 2 | `PyMuPDF` (fitz) | pdfplumber 不可用时的备选，也能取文字 |
| 3 | `pytesseract` + Tesseract-OCR | 扫描件 PDF / 图片简历，需额外安装 Tesseract 引擎 |

**图片 OCR**：

```
图片文件（.png/.jpg/.jpeg/.webp/.bmp）
    │
    ▼
pytesseract.image_to_string(img, lang="chi_sim+eng")
```

> 需要系统安装 Tesseract-OCR 引擎，否则抛 `RuntimeError` 提示安装。

#### 第二段：文本 → 结构化（`parse_resume_with_llm`）

```
简历文本（截断至 8000 字符）
    │
    ▼
RESUME_PARSE_PROMPT.format(resume_text=...)
    │
    ▼
LLM.chat(prompt, task_type="skill_extraction", temperature=0.1, json_mode=True)
    │
    ▼
_safe_json_parse()   ← 容错：剥离 ```json 包裹、截取首个 { 到末个 }
    │
    ▼
_normalize_parsed()  ← 归一化：过滤 None/非法类型、缺字段补默认值
    │
    ▼
返回 ParsedResumeData 兼容 dict
```

**`_normalize_parsed` 防御逻辑**：

| 字段类型 | 防御策略 |
|---------|---------|
| `skills` | 过滤 `None`、非 `str`、空串；字符串形式 `"Python,Java"` 自动拆分 |
| `experiences` | 过滤 `None`、非 `dict` 元素；子字段缺失时兜底 |
| `educations` | 同上 |
| 整数字段 | `opt_int()`：`None`/空串 → `None`，字符串 `"28"` → `28` |
| 字符串字段 | `opt_str()`：`None` → `None`，统一类型 |

---

### 4.2 `models/prompts.py` — `RESUME_PARSE_PROMPT`

关键设计：

- 明确列出 13 项抽取规则 + 取值说明（如 gender: 0=男 1=女）
- 给出完整 JSON 示例，LLM 按示例格式输出
- 禁止 Markdown 代码块和多余文字
- 配合 `response_format={"type":"json_object"}` 保证输出合法 JSON

---

### 4.3 `models/schemas.py` — Pydantic 模型

| 类名 | 用途 |
|------|------|
| `ResumeExperienceItem` | 单条工作经历 |
| `ResumeEducationItem` | 单条教育经历 |
| `ParsedResumeData` | 完整解析结果（含 skills/experiences/educations 数组 + parsed_raw） |
| `AnalyzeResumeRequest` | JSON 方式调用的请求体（file_url + file_type） |

---

### 4.4 `utils/config.py` — 配置项

```python
UPLOAD_DIR = "data/uploads/resumes"          # 上传文件存储目录

RESUME_ANALYZE_CONFIG = {
    "allowed_pdf_ext": {".pdf"},             # 允许的 PDF 扩展名
    "allowed_image_ext": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
    "max_file_size": 10 * 1024 * 1024,       # 10MB 上限
    "ocr_enabled": True,                     # OCR 开关
    "llm_task_type": "skill_extraction",     # 复用 MODEL_ROUTER 的任务类型
    "use_json_mode": True,                   # 开启 LLM JSON 模式
}
```

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| UPLOAD_DIR | `UPLOAD_DIR` | `data/uploads/resumes` | 上传目录 |
| max_file_size | `RESUME_MAX_FILE_SIZE` | 10485760 (10MB) | 单文件大小上限 |
| ocr_enabled | `RESUME_OCR_ENABLED` | true | OCR 开关 |
| llm_task_type | `RESUME_LLM_TASK_TYPE` | skill_extraction | LLM 路由任务类型 |
| use_json_mode | `RESUME_JSON_MODE` | true | JSON 模式开关 |

---

## 五、文件清单

| 文件 | 动作 | 关键内容 |
|------|------|---------|
| `core/resume_parser.py` | **新建** | 两段式解析：extract_resume_text + parse_resume_with_llm |
| `models/prompts.py` | 追加 | `RESUME_PARSE_PROMPT` 模板 |
| `models/schemas.py` | 追加 | 4 个 Pydantic 模型 |
| `api/agent_routes.py` | 追加 | 2 个路由 + `_api_ok` / `_api_err` 辅助函数 |
| `utils/config.py` | 追加 | `UPLOAD_DIR` + `RESUME_ANALYZE_CONFIG` |
| `requirements.txt` | 追加 | `pdfplumber` / `PyMuPDF` / `python-multipart` |

> **未修改的文件**：`api/main.py`（agent_router 已挂载）、`services/db_service.py`（表结构已就绪）、所有 agent/* 和 service/*。

---

## 六、依赖安装

```bash
pip install pdfplumber PyMuPDF python-multipart
```

| 包 | 版本 | 用途 |
|----|------|------|
| `pdfplumber` | ≥0.11.0 | PDF 文本提取主力 |
| `PyMuPDF` | ≥1.24.0 | PDF 提取兜底 + 扫描件渲染 |
| `python-multipart` | ≥0.0.6 | FastAPI UploadFile 必需 |

**可选依赖**（图片/扫描件 OCR）：

```bash
pip install pytesseract
# 另需安装 Tesseract-OCR 引擎：https://github.com/tesseract-ocr/tesseract
```

---

## 七、联调步骤

### 7.1 启动服务

```bash
# 强制 SQLite（避开 MySQL 连接问题）
MYSQL_HOST=127.0.0.1 MYSQL_PORT=1 MYSQL_USER=x MYSQL_PASSWORD=x \
  python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### 7.2 测试解析（只返回不入库）

```bash
# 上传 PDF
curl -X POST http://localhost:8001/agents/analyze-resume \
  -F "file=@resume.pdf"

# JSON 传路径
curl -X POST http://localhost:8001/agents/analyze-resume \
  -H "Content-Type: application/json" \
  -d '{"file_url":"data/uploads/resumes/resume.pdf","file_type":"pdf"}'
```

### 7.3 测试解析+入库

```bash
curl -X POST http://localhost:8001/agents/analyze-resume-and-save \
  -F "user_id=1" \
  -F "file=@resume.pdf"
```

### 7.4 验证入库数据

```python
from services.db_service import get_db_service
db = get_db_service()
resume = db.get_resume(resume_id)              # 主表
skills = db.get_resume_skills(resume_id)       # 技能关联
exps   = db.get_resume_experiences(resume_id)  # 工作经历
edus   = db.get_resume_educations(resume_id)   # 教育经历
```

### 7.5 错误用例验证

| 操作 | 预期 |
|------|------|
| 上传 `.txt` 文件 | `code:400, "不支持的文件类型: .txt"` |
| 传不存在的路径 | `code:500, "文件不存在或无法读取"` |
| 不传任何文件 | `code:400, "未提供文件"` |
| 上传空内容 PDF | `code:500, "简历内容为空"` |

---

## 八、注意事项

1. **职责边界**：`/analyze-resume` 只抽取返回，不写库。JobHunter 调用后自行做字典匹配和入库。
2. **JSON 模式**：智谱 glm-4 支持 `response_format={"type":"json_object"}`，开启后输出合法 JSON 概率高；`_safe_json_parse` 兜底处理偶尔的格式异常。
3. **PDF 扫描件**：pdfplumber/PyMuPDF 提不出文字时，自动走「渲染图片 → pytesseract OCR」。环境未装 Tesseract 会明确报 `RuntimeError`。
4. **文件安全**：上传文件名用 UUID 重命名防路径穿越；大小限制 10MB（可配置）。
5. **文本截断**：简历文本超过 8000 字符截断，防 LLM token 超限。
6. **LLM 依赖**：需配置有效的 `ZHIPU_API_KEY`（或 `LLM_API_KEY`），否则返回 `code:500`。
7. **双库兼容**：不直接写 SQL，全部走 `db_service` 的 CRUD 方法，MySQL/SQLite 自动兼容。
8. **不破坏现有**：仅追加路由和文件，`api/main.py` 无需改动。
