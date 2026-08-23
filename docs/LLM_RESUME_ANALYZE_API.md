# LLM 服务接口需求：简历智能解析

> 本文档用于 JobHunter 与 LLM 服务的接口对接。
> **JobHunter 已完成**：文件上传、存储、状态机（pending→parsing→done/failed）。
> **需要 LLM 实现**：读取简历文件 → 大模型抽取 → 返回结构化数据。

---

## 一、为什么需要这个接口

JobHunter 端只负责"文件存取"，没有 PDF 解析库，也没有调用大模型的逻辑。
所以由 **LLM 服务** 承担"PDF → 文本 → 结构化数据"的 AI 工作，返回 JSON 给 JobHunter 入库。

```
用户上传 PDF
    ↓
JobHunter(8000): 存文件 + 建记录(pending)
    ↓ (异步调用 LLM)
LLM 服务(8001): 读 PDF → 调大模型抽取 → 返回结构化 JSON
    ↓
JobHunter(8000): 收到 JSON → 字典匹配 → 入 resume_skills 表 → 状态改 done
```

---

## 二、接口定义

### `POST /agents/analyze-resume`

**路径前缀**：与现有 agent 路由一致，完整路径为 `/agents/analyze-resume`
（前端经 vite proxy 转发，前端调用 `/api/agents/analyze-resume`）

### 请求（JobHunter → LLM）

**Body (JSON)**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_url` | string | 是 | 简历文件的可访问 URL 或本地路径 |
| `file_type` | string | 否 | 文件类型：`pdf` / `image`（图片需 OCR） |

**示例**：
```json
{
  "file_url": "http://127.0.0.1:8000/uploads/resumes/abc123.pdf",
  "file_type": "pdf"
}
```

> ⚠️ 注意：JobHunter 的 `uploads/` 目录默认不对外暴露。
> 方案一：JobHunter 提供一个**临时签名下载接口**给 LLM 拉取。
> 方案二：LLM 直接按文件路径读取同一台机器的文件系统（最简单，本地部署够用）。

---

### 响应（LLM → JobHunter）

**统一返回结构**（与 LLM 现有 `/api/v1/...` 风格一致）：

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
    "skills": ["Python", "Java", "Vue", "Docker"],
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
    "parsed_raw": { "...原始LLM解析结果，原样透传存库..." }
  }
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 姓名（抽不到给 `null`） |
| `gender` | int | 否 | 性别：0男 1女（抽不到给 `null`） |
| `age` | int | 否 | 年龄 |
| `phone` / `email` | string | 否 | 联系方式 |
| `city` | string | 否 | 当前所在城市 |
| `work_years` | int | 否 | 工作年限 |
| `education` | string | 否 | 最高学历（专科/本科/硕士/博士） |
| `expect_*` | - | 否 | 求职意向 |
| **`skills`** | string[] | **是** | **技能名称列表**（中文/英文均可，JobHunter 会做字典归一化） |
| `experiences` | array | 否 | 工作经历列表 |
| `educations` | array | 否 | 教育经历列表 |
| `parsed_raw` | object | 否 | 大模型原始返回，原样存库用于排查/复现 |

---

## 三、JobHunter 端会怎么处理这份返回

接到这份 JSON 后，JobHunter 会做：

1. **更新 resumes 主表**：`name / age / city / work_years ...` 等字段
2. **字典匹配 skills**：把 `"Python"` 匹配到 `skills` 字典的 `skill_id`
3. **写入 `resume_skills` 表**：`(resume_id, skill_id)` 关联
4. **写入 `resume_experiences` 表**：工作经历明细
5. **写入 `resume_educations` 表**：教育经历明细
6. **状态更新**：`parse_status = "done"`

> 所以 LLM 只管"抽取和返回"，**归一化和入库由 JobHunter 负责**。

---

## 四、错误处理

| 场景 | HTTP 状态码 | code | message |
|------|------------|------|---------|
| 解析成功 | 200 | 0 | 解析成功 |
| 文件读取失败 | 200 | 500 | 文件不存在或无法读取 |
| PDF 文本提取为空 | 200 | 500 | 简历内容为空 |
| 大模型调用超时/失败 | 200 | 500 | 简历分析服务异常 |

> 约定：**HTTP 始终返回 200**，业务成败看 `code` 字段（和 LLM 现有约定一致）。
> JobHunter 收到 `code != 0` 会把简历状态置为 `failed`，并记录 `parse_error`。

---

## 五、技术建议（给队友的参考实现）

### 1. PDF 文本提取

推荐使用 **`pdfplumber`** 或 **`PyMuPDF (fitz)`**，轻量高效：

```python
import pdfplumber

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text
```

### 2. 图片简历 OCR（可选）

如需支持图片简历，推荐 **`PaddleOCR`** 或 **`tesseract`**。

### 3. 大模型 Prompt 模板（建议让大模型输出 JSON）

```
你是一个专业的简历解析助手。请从以下简历文本中提取结构化信息。
严格按 JSON 格式输出，不要包含多余文字。

简历文本：
{resume_text}

输出 JSON 格式：
{
  "name": "姓名",
  "phone": "电话",
  "email": "邮箱",
  "skills": ["技能1", "技能2"],
  "experiences": [{"company_name":"公司","title":"职位","start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD","description":"工作内容"}],
  "educations": [{"school":"学校","major":"专业","degree":"学历","start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD"}]
}
```

> 建议大模型开启 `response_format={"type": "json_object"}`，保证输出是合法 JSON。

---

## 六、联调步骤

1. **LLM 侧**：实现 `POST /agents/analyze-resume` 接口
2. **JobHunter 侧**：新增轮询时调用此接口的逻辑（JobHunter 这边自己实现）
3. **联调测试**：
   - JobHunter 上传一个简历 PDF
   - 手动 curl 调用 LLM 接口，确认能返回结构化 JSON
   - JobHunter 端跑通"上传 → 调 LLM → 入库 → 状态变 done"全流程

---

## 七、附：JobHunter 端的数据表结构（供 LLM 参考）

> LLM **不需要操作这些表**，只需要按上面的格式返回 JSON。
> 这里列出表结构，是让 LLM 知道"这些字段最终会被怎么使用"。

```sql
-- 简历主表（LLM 返回的 name/age 等会更新到这里）
resumes(id, user_id, name, gender, age, city, phone, email,
        work_years, education, expect_salary_min, expect_salary_max,
        expect_city, expect_job, parse_status, parse_error, parsed_raw)

-- 简历技能关联（LLM 返回的 skills 会经过字典匹配后写入）
resume_skills(resume_id, skill_id, proficiency, years)

-- 工作经历（LLM 返回的 experiences 直接写入）
resume_experiences(resume_id, company_name, title, start_date, end_date, description, is_current)

-- 教育经历（LLM 返回的 educations 直接写入）
resume_educations(resume_id, school, major, degree, start_date, end_date)
```
