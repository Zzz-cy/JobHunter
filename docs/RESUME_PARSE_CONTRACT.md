# 简历解析接口契约（Python ↔ LLM）

> **用途**：Python 后端（FastAPI）与 LLM 后端（队友）之间的接口约定。
> 双方照此文档开发，联调时按此对齐。
> **最后更新**：2026-07-31

---

## 目录

- [一、部署说明（同机开发）](#一部署说明同机开发)
- [二、接口总览](#二接口总览)
- [三、Python → LLM：请求解析](#三python--llm请求解析)
- [四、LLM → Python：返回结果](#四llm--python返回结果)
- [五、数据结构详解](#五数据结构详解)
- [六、状态机](#六状态机)
- [七、错误处理](#七错误处理)
- [八、技能归一说明](#八技能归一说明)
- [九、测试用例](#九测试用例)
- [十、未来演进](#十未来演进)

---

## 一、部署说明（同机开发）

**当前阶段**：Python 后端、LLM 后端、MySQL 都运行在同一台电脑上。

```
┌─────────────────────────────────────────────────────┐
│  同一台电脑                                         │
│                                                     │
│  Python 后端 (FastAPI, 端口 8000)                   │
│    ├── uploads/resumes/xxx.pdf   ← 简历存这里        │
│    └── httpx 调 LLM                                │
│          ↓                                          │
│  LLM 后端 (端口待定, 比如待定)                      │
│    ├── 直接读本地文件                               │
│    └── 返回 JSON                                    │
│                                                     │
│  MySQL (端口 3306)                                  │
└─────────────────────────────────────────────────────┘
```

### 文件传递方案：传本地路径（方式 A）

**当前方案**：Python 后端把文件的**本地绝对路径**传给 LLM 后端，LLM 后端直接读本地文件。

**理由**：
- 同机部署，文件系统共享
- 最快、最简单（只传路径字符串）
- 省带宽（不传文件内容）

**限制**（技术债，先欠着）：
- 两服务必须同机、同文件系统
- 未来部署到不同服务器时，要改成传 URL（见第十节）

---

## 二、接口总览

LLM 后端只需提供 **1 个接口**：

| 接口 | 方法 | 作用 |
|---|---|---|
| `/agents/analyze-resume` | POST | 接收文件路径，返回解析后的 JSON |

**Python 后端调用时机**：简历上传成功后（`parse_status` 从 `pending` → `parsing`）。

---

## 三、Python → LLM：请求解析

### 请求

```
POST http://localhost:8001/agents/analyze-resume
Content-Type: application/json
```

### 请求体

```json
{
    "file_url": "C:/GitHub/JobHunter/backend/uploads/resumes/abc123.pdf",
    "file_type": "pdf"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file_url` | string | 是 | 文件**本地绝对路径**，LLM 直接 `open()` 读（队友接口字段名是 `file_url`） |
| `file_type` | string | 否 | 文件类型：`pdf` / `image`，不传则按扩展名推断 |

### 注意事项

- **`file_url` 必须是绝对路径**（Python 后端拼接 `settings.UPLOAD_DIR` 的绝对路径）
- **LLM 后端要有文件读权限**（同机部署默认有）
- **超时**：AI 解析慢，Python 侧 `timeout=120`（2 分钟）
- 队友接口也支持 multipart 上传文件，但我们用 JSON 传路径（同机最优）

---

## 四、LLM → Python：返回结果

### 成功响应

**HTTP 200**，返回结构化 JSON：

```json
{
    "code": 0,
    "message": "解析成功",
    "data": {
        "name": "李伟",
        "gender": 0,
        "age": 28,
        "phone": "138****8000",
        "email": "liwei@example.com",
        "city": "北京",
        "work_years": 5,
        "education": "本科",

        "experiences": [
            {
                "company": "字节跳动",
                "title": "Python 后端工程师",
                "start_date": "2021-03",
                "end_date": "2024-05",
                "description": "负责电商后端，高并发系统设计"
            }
        ],

        "educations": [
            {
                "school": "北京邮电大学",
                "major": "计算机科学与技术",
                "degree": "本科",
                "start_date": "2016-09",
                "end_date": "2020-06"
            }
        ],

        "skills": ["Python", "Django", "MySQL", "Docker", "Redis"]
    }
}
```

### 字段说明

| 字段 | 类型 | 可空 | 说明 | 对应数据库 |
|---|---|---|---|---|
| `name` | string | ❌ | 姓名 | resumes.name |
| `gender` | int | ✅ | 性别（0=男，1=女） | resumes.gender |
| `age` | int | ✅ | 年龄 | resumes.age |
| `phone` | string | ✅ | 手机号 | resumes.phone |
| `email` | string | ✅ | 邮箱 | resumes.email |
| `city` | string | ✅ | 现居城市 | resumes.city |
| `work_years` | int | ✅ | 工作年限 | resumes.work_years |
| `education` | string | ✅ | 最高学历（大专/本科/硕士/博士） | resumes.education |
| `experiences` | array | ✅ | 工作经历（多条） | resume_experiences |
| `educations` | array | ✅ | 教育经历（多条） | resume_educations |
| `skills` | array | ✅ | 技能名列表 | resume_skills（需归一） |

### 失败响应

**HTTP 200**（业务失败也返回 200，用 code 区分）：

```json
{
    "code": 500,
    "message": "文件解析失败：PDF 损坏",
    "data": null
}
```

| code | 含义 |
|---|---|
| 0 | 成功 |
| 非 0 | 失败（message 给错误原因） |

---

## 五、数据结构详解

### experiences（工作经历）字段

```json
{
    "company_name": "字节跳动",
    "title": "Python 后端工程师",
    "start_date": "2021-03",
    "end_date": "2024-05",
    "description": "负责电商后端，高并发系统设计"
}
```

| 字段 | 类型 | 可空 | 说明 |
|---|---|---|---|
| `company_name` | string | ❌ | 公司名称（注意是 `company_name` 不是 `company`） |
| `title` | string | ✅ | 职位名称 |
| `start_date` | string | ✅ | 入职时间（格式 `YYYY-MM`） |
| `end_date` | string | ✅ | 离职时间（在职为空） |
| `description` | string | ✅ | 工作内容 |

### educations（教育经历）字段

```json
{
    "school": "北京邮电大学",
    "major": "计算机科学与技术",
    "degree": "本科",
    "start_date": "2016-09",
    "end_date": "2020-06"
}
```

| 字段 | 类型 | 可空 | 说明 |
|---|---|---|---|
| `school` | string | ❌ | 学校名称 |
| `major` | string | ✅ | 专业 |
| `degree` | string | ✅ | 学历（大专/本科/硕士/博士） |
| `start_date` | string | ✅ | 入学时间（`YYYY-MM`） |
| `end_date` | string | ✅ | 毕业时间（`YYYY-MM`） |

### skills（技能）说明

```json
"skills": ["Python", "Django", "MySQL", "Docker", "Redis"]
```

- 返回**技能名字符串数组**
- **不需要返回 skill_id**（Python 后端负责技能归一，见第八节）
- 技能名尽量用**常见写法**（如 "Python" 不要 "python3.x"）

---

## 六、状态机

Python 后端的 `resumes.parse_status` 字段流转：

```
pending ──上传成功──> parsing ──LLM返回成功──> done
                        │
                        └────LLM返回失败/超时──> failed
```

| 状态 | 触发时机 | 谁触发 |
|---|---|---|
| `pending` | 文件刚上传 | Python 上传接口 |
| `parsing` | 调 LLM 解析前 | Python |
| `done` | LLM 返回成功 | Python |
| `failed` | LLM 返回失败/超时/异常 | Python |

**LLM 后端不碰状态机**，只管"收请求 → 返回 JSON"。状态流转全由 Python 控制。

---

## 七、错误处理

### Python 侧要处理的情况

| 情况 | 处理 |
|---|---|
| LLM 服务连不上 | `parse_status=failed`，`parse_error="LLM 服务不可达"` |
| LLM 返回 code != 0 | `parse_status=failed`，`parse_error=llm 返回的 message` |
| LLM 超时（>120s） | `parse_status=failed`，`parse_error="解析超时"` |
| LLM 返回的 JSON 缺字段 | 用默认值/null 填充，不报错 |

**原则**：**解析失败不影响上传**。上传成功就返回前端，解析失败只改状态，前端轮询能看到。

---

## 八、技能归一说明

⚠️ **这是 Python 后端的责任，不是 LLM 的**。

LLM 返回的技能名可能是各种写法：

```
LLM 抽出: ["Python3", "Django框架", "mysql", "docker"]
```

Python 后端要映射到 `skills` 字典表的标准技能：

```
字典表 skills:
  - id=1, name="Python", alias="py,python3,python3.x"
  - id=7, name="Django", alias="django,django框架"
  - id=10, name="MySQL", alias="mysql"

归一后存 resume_skills:
  - resume_id=1, skill_id=1 (Python)
  - resume_id=1, skill_id=7 (Django)
  - resume_id=1, skill_id=10 (MySQL)
```

**找不到的技能**（字典表没有）：记录日志，跳过（或后续扩充字典）。

---

## 九、测试用例

### 测试 1：正常解析

```
请求:
POST /parse
{
    "resume_id": 1,
    "file_path": "C:/GitHub/JobHunter/backend/uploads/resumes/test.pdf",
    "source_type": "pdf"
}

预期响应:
{
    "code": 0,
    "data": {
        "name": "李伟",
        "skills": ["Python", "Django"],
        ...
    }
}
```

### 测试 2：文件不存在

```
请求:
{
    "file_path": "C:/xxx/not_exist.pdf",
    ...
}

预期响应:
{
    "code": 500,
    "message": "文件不存在: C:/xxx/not_exist.pdf"
}
```

### 测试 3：PDF 损坏

```
预期响应:
{
    "code": 500,
    "message": "PDF 文件损坏，无法解析"
}
```

---

## 十、未来演进

### 当前（同机开发）：传文件路径

```json
{ "file_path": "C:/GitHub/JobHunter/backend/uploads/resumes/xxx.pdf" }
```

### 未来（生产部署）：传 URL

```json
{ "file_url": "https://api.jobhunter.com/uploads/resumes/xxx.pdf" }
```

**LLM 后端代码改动**：从 `open(path)` 改成 `requests.get(url)` 下载。

**切换时机**：部署到不同服务器时。

---

## 附：联调清单

- [ ] LLM 后端启动，监听端口确认
- [ ] Python 后端能 `httpx.post` 到 LLM（网络通）
- [ ] LLM 能读 `file_path` 指定的文件（权限通）
- [ ] LLM 返回的 JSON 格式符合第四节约定
- [ ] Python 能解析 JSON 并存入 4 张表
- [ ] 技能归一能正确映射到字典表
- [ ] 失败场景（文件损坏/超时）正确处理

---

**文档版本**：v1.0
**Python 负责**：调用 LLM + 拆 JSON 存表 + 状态机
**LLM 负责**：读文件 + 解析 + 返回 JSON
**约定**：双方严格按此文档开发，格式变更需双方确认
