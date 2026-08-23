# 简历解析 API 接口文档

> 基于代码 `api/agent_routes.py` 自动生成，服务默认端口 `8001`，路由前缀 `/agents`

---

## 1. 简历智能解析（纯解析，不入库）

### 基本信息

| 项目 | 说明 |
|------|------|
| **URL** | `POST /agents/analyze-resume` |
| **功能** | 上传或指定简历文件，经 LLM 抽取为结构化数据，不入库 |
| **响应格式** | HTTP 始终 200，业务成败看 `code` 字段 |

### 调用方式（三选一）

#### 方式 A：上传文件（multipart/form-data）

```bash
curl -X POST http://localhost:8001/agents/analyze-resume \
  -F "file=@/path/to/resume.pdf"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | UploadFile | 是 | 上传的简历文件（PDF/图片） |

#### 方式 B：表单传本地路径（multipart/form-data）

```bash
curl -X POST http://localhost:8001/agents/analyze-resume \
  -F "file_url=/path/to/resume.pdf" \
  -F "file_type=pdf"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_url` | string | 是 | 简历文件的本地绝对路径 |
| `file_type` | string | 否 | 文件类型：`pdf` / `image`，不传则按扩展名自动推断 |

#### 方式 C：JSON 传路径（application/json）

```bash
curl -X POST http://localhost:8001/agents/analyze-resume \
  -H "Content-Type: application/json" \
  -d '{"file_url": "/path/to/resume.pdf", "file_type": "pdf"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_url` | string | 是 | 简历文件的本地绝对路径 |
| `file_type` | string | 否 | 文件类型：`pdf` / `image`，不传则按扩展名自动推断 |

> **注意**：三种方式互斥，优先级为 方式A > 方式B > 方式C。若同时传了 `file` 和 `file_url`，以 `file` 上传为准。

### 支持的文件类型

| 类型 | 扩展名 |
|------|--------|
| PDF | `.pdf` |
| 图片 | `.jpg` `.jpeg` `.png` `.bmp` `.tiff` |

### 成功响应

```json
{
    "code": 0,
    "message": "解析成功",
    "data": {
        "name": "张三",
        "gender": 1,
        "age": 28,
        "phone": "13800138000",
        "email": "zhangsan@example.com",
        "city": "北京",
        "work_years": 5,
        "education": "本科",
        "expect_salary_min": 15000,
        "expect_salary_max": 25000,
        "expect_city": "北京",
        "expect_job": "Python后端工程师",
        "skills": ["Python", "Django", "MySQL", "Redis", "Docker"],
        "experiences": [
            {
                "company_name": "XX科技有限公司",
                "title": "高级后端工程师",
                "start_date": "2020-03",
                "end_date": "2023-06",
                "description": "负责核心业务系统开发与维护",
                "is_current": 0
            }
        ],
        "educations": [
            {
                "school": "XX大学",
                "major": "计算机科学与技术",
                "degree": "本科",
                "start_date": "2016-09",
                "end_date": "2020-06"
            }
        ],
        "parsed_raw": { }
    },
    "request_id": "a1b2c3d4",
    "timestamp": "2026-07-31T10:30:00.000000"
}
```

### 失败响应

```json
{
    "code": 400,
    "message": "不支持的文件类型: .doc",
    "data": null,
    "request_id": "a1b2c3d4",
    "timestamp": "2026-07-31T10:30:00.000000"
}
```

### 错误码说明

| code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误（未提供文件、文件类型不支持、简历内容为空） |
| 500 | 服务异常（文件不存在、PDF解析失败、LLM调用失败、LLM返回非法JSON） |

### 响应 data 字段详情

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string \| null | 姓名 |
| `gender` | int \| null | 性别（1=男，2=女） |
| `age` | int \| null | 年龄 |
| `phone` | string \| null | 手机号 |
| `email` | string \| null | 邮箱 |
| `city` | string \| null | 所在城市 |
| `work_years` | int \| null | 工作年限 |
| `education` | string \| null | 最高学历 |
| `expect_salary_min` | int \| null | 期望薪资下限 |
| `expect_salary_max` | int \| null | 期望薪资上限 |
| `expect_city` | string \| null | 期望城市 |
| `expect_job` | string \| null | 期望岗位 |
| `skills` | string[] | 技能列表 |
| `experiences` | object[] | 工作经历列表 |
| `educations` | object[] | 教育经历列表 |
| `parsed_raw` | object \| null | LLM 原始返回（调试用） |

#### experiences 子项

| 字段 | 类型 | 说明 |
|------|------|------|
| `company_name` | string | 公司名称 |
| `title` | string \| null | 职位 |
| `start_date` | string \| null | 开始日期 |
| `end_date` | string \| null | 结束日期 |
| `description` | string \| null | 工作描述 |
| `is_current` | int \| null | 是否在职（1=是，0=否） |

#### educations 子项

| 字段 | 类型 | 说明 |
|------|------|------|
| `school` | string | 学校名称 |
| `major` | string \| null | 专业 |
| `degree` | string \| null | 学历 |
| `start_date` | string \| null | 开始日期 |
| `end_date` | string \| null | 结束日期 |

---

## 2. 简历解析并入库

### 基本信息

| 项目 | 说明 |
|------|------|
| **URL** | `POST /agents/analyze-resume-and-save` |
| **功能** | 上传简历文件 → LLM 抽取 → 写入数据库（resumes / resume_skills / resume_experiences / resume_educations） |
| **Content-Type** | `multipart/form-data` |

### 请求参数

```bash
curl -X POST http://localhost:8001/agents/analyze-resume-and-save \
  -F "user_id=1" \
  -F "file=@/path/to/resume.pdf"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | int | 是 | 用户ID |
| `file` | UploadFile | 是 | 上传的简历文件（PDF/图片） |

### 成功响应

```json
{
    "code": 0,
    "message": "解析并入库成功",
    "data": {
        "resume_id": 1,
        "skill_count": 5,
        "experience_count": 2,
        "education_count": 1,
        "parsed": {
            "name": "张三",
            "gender": 1,
            "age": 28,
            "phone": "13800138000",
            "email": "zhangsan@example.com",
            "city": "北京",
            "work_years": 5,
            "education": "本科",
            "expect_salary_min": 15000,
            "expect_salary_max": 25000,
            "expect_city": "北京",
            "expect_job": "Python后端工程师",
            "skills": ["Python", "Django", "MySQL"],
            "experiences": [ ],
            "educations": [ ],
            "parsed_raw": { }
        }
    },
    "request_id": "a1b2c3d4",
    "timestamp": "2026-07-31T10:30:00.000000"
}
```

### 失败响应

```json
{
    "code": 500,
    "message": "简历分析服务异常: ...",
    "data": null,
    "request_id": "a1b2c3d4",
    "timestamp": "2026-07-31T10:30:00.000000"
}
```

### 入库流程

1. **保存文件** — 上传文件存入 `UPLOAD_DIR`，文件名用 UUID 防冲突
2. **LLM 抽取** — 调用 `analyze_resume_file()` 解析结构化数据
3. **写入 resumes 主表** — 包含姓名、性别、年龄、城市、手机、邮箱、工作年限、学历、期望薪资等
4. **写入 resume_skills** — 抽取的技能名先在 skills 表精确匹配，匹配不到则新建
5. **写入 resume_experiences** — 工作经历逐条入库
6. **写入 resume_educations** — 教育经历逐条入库

### 响应 data 字段详情

| 字段 | 类型 | 说明 |
|------|------|------|
| `resume_id` | int | 入库后的简历ID |
| `skill_count` | int | 技能数量 |
| `experience_count` | int | 工作经历数量 |
| `education_count` | int | 教育经历数量 |
| `parsed` | object | LLM 解析的完整结构化数据（同接口1的 data） |

---

## 3. 统一响应格式

所有简历接口遵循统一响应结构：

```json
{
    "code": 0,
    "message": "success",
    "data": { },
    "request_id": "",
    "timestamp": "2026-07-31T10:30:00.000000"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，`0` = 成功，非 0 = 失败 |
| `message` | string | 状态描述 |
| `data` | object \| null | 业务数据，失败时为 null |
| `request_id` | string | 请求追踪ID（取自请求头 `X-Request-ID`，未传则自动生成） |
| `timestamp` | string | 响应时间（ISO 8601 格式） |

---

## 4. 解析流程说明

```
文件上传/路径指定
       │
       ▼
┌──────────────────┐
│  文件 → 文本提取   │  core/resume_parser.py: extract_resume_text()
│  PDF: pdfplumber  │  主力提取，PyMuPDF 兜底
│  图片: OCR        │  pytesseract + Tesseract-OCR
│  扫描件PDF: OCR   │  PyMuPDF 渲染图片 → OCR
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  文本 → LLM 结构化 │  core/resume_parser.py: parse_resume_with_llm()
│  发送解析 Prompt   │  models/prompts.py: RESUME_PARSE_PROMPT
│  JSON mode 输出   │  temperature=0.1, max_tokens=4096
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  结果归一化        │  core/resume_parser.py: _normalize_parsed()
│  缺字段补默认值    │  过滤非法元素
│  容错 JSON 解析   │  剥离 markdown 代码块
└──────────────────┘
       │
       ▼
   返回结构化数据
```

---

## 5. 相关代码文件索引

| 文件 | 说明 |
|------|------|
| `api/agent_routes.py` | API 路由定义（接口入口） |
| `core/resume_parser.py` | 核心解析逻辑（文件→文本→LLM结构化） |
| `models/schemas.py` | 数据模型定义（ParsedResumeData 等） |
| `models/prompts.py` | LLM 解析 Prompt 模板 |
| `services/db_service.py` | 数据库入库操作（接口2使用） |
| `utils/config.py` | 配置（端口、允许的文件类型、上传目录等） |
