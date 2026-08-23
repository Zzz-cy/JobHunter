# 新增功能：PDF/图片简历智能解析

> **目标**：实现 `POST /agents/analyze-resume` 接口，接收 PDF 或图片简历文件，
> 经 LLM 抽取后返回 `LLM_RESUME_ANALYZE_API.md` 定义的结构化字段（对应 `DATABASE_SCHEMA.md` 的 resumes 主表 + 三个子表）。
> **原则**：增量扩展，复用现有 `db_service` / `llm_service`，不动已有路由和表结构。
> **依据**：`check/LLM_RESUME_ANALYZE_API.md`（接口契约）、`check/DATABASE_SCHEMA.md`（字段定义）。

---

## 一、需求拆解

### 1.1 输入

两种接受方式（同时支持，路由参数二选一）：

| 方式 | 场景 | 说明 |
|------|------|------|
| **multipart/form-data 上传文件** | 前端直接传 PDF/图片 | 推荐主用方式；存到 `data/uploads/resumes/` |
| **JSON 传 `file_url` 本地路径** | JobHunter 已存好文件，LLM 按路径读 | 兼容 `LLM_RESUME_ANALYZE_API.md` 第二节契约 |

`file_type` 自动从扩展名推断：`.pdf` → pdf；`.png/.jpg/.jpeg/.webp/.bmp` → image；其它 → 报错。

### 1.2 输出（严格对齐 `LLM_RESUME_ANALYZE_API.md` 第二、三节）

```json
{
  "code": 0,
  "message": "解析成功",
  "data": {
    "name": "张三", "gender": 0, "age": 28,
    "phone": "13800138000", "email": "zhangsan@example.com",
    "city": "北京", "work_years": 5, "education": "本科",
    "expect_salary_min": 20000, "expect_salary_max": 30000,
    "expect_city": "北京", "expect_job": "高级Python开发工程师",
    "skills": ["Python", "Java", "Vue", "Docker"],
    "experiences": [{"company_name":"字节跳动","title":"后端工程师","start_date":"2022-06-01","end_date":"2024-08-01","description":"...","is_current":0}],
    "educations": [{"school":"浙江大学","major":"计算机科学与技术","degree":"本科","start_date":"2018-09-01","end_date":"2022-06-01"}],
    "parsed_raw": { "...原始LLM返回..." }
  }
}
```

> ⚠️ 本接口**只抽取、返回**，**不写库**。归一化与入库由调用方（JobHunter）负责（见 `LLM_RESUME_ANALYZE_API.md` 第三节）。
> 但为方便单机联调，**额外提供一个入库版端点** `POST /agents/analyze-resume-and-save`（见步骤 4），内部走 db_service 直接入库，便于验证字段正确性。

### 1.3 错误约定（对齐第四节）

HTTP 始终 200，业务成败看 `code`：

| 场景 | code | message |
|------|------|---------|
| 成功 | 0 | 解析成功 |
| 文件读取失败 | 500 | 文件不存在或无法读取 |
| 文本为空 | 500 | 简历内容为空 |
| LLM 调用失败 | 500 | 简历分析服务异常 |
| 类型不支持 | 400 | 不支持的文件类型 |

---

## 二、要改/新增的文件清单

| # | 文件 | 动作 | 说明 |
|---|------|------|------|
| 1 | `requirements.txt`（或 `pyproject.toml`） | 新增依赖 | `pdfplumber`、`PyMuPDF`（兜底）、`python-multipart` |
| 2 | `utils/config.py` | 新增配置 | `UPLOAD_DIR`、`RESUME_ANALYZE_CONFIG` |
| 3 | `models/prompts.py` | 新增 | `RESUME_PARSE_PROMPT` 模板 |
| 4 | `models/schemas.py` | 新增 | `ResumeExperienceItem`、`ResumeEducationItem`、`ParsedResumeData`、`AnalyzeResumeRequest` |
| 5 | `core/resume_parser.py` | **新建** | 文件→文本（PDF/图片OCR）、文本→结构化（调 LLM） |
| 6 | `api/agent_routes.py` | 新增路由 | `/agents/analyze-resume`、`/agents/analyze-resume-and-save` |
| 7 | `services/db_service.py` | 微调（可选） | 新增 `save_parsed_resume()` 一站式入库方法 |
| 8 | `alembic/versions/` | 无需改动 | 表结构已含全部所需字段（resumes/resume_skills/resume_experiences/resume_educations），上轮迁移已完成 |

> **不动**的文件：`api/main.py`（agent_router 已挂载，新路由自动生效）、所有 agent/* 、其它 service/* 。

---

## 三、详细步骤

### 步骤 1：安装依赖

在项目根目录执行（让用户用 `!` 前缀跑也行）：

```bash
pip install pdfplumber PyMuPDF python-multipart
```

- `pdfplumber`：PDF 文本提取主力（`LLM_RESUME_ANALYZE_API.md` 第五节推荐）
- `PyMuPDF` (import 名 `fitz`)：pdfplumber 提不出文字（扫描件）时的兜底，且可把 PDF 渲染成图片给 OCR
- `python-multipart`：FastAPI 处理 `UploadFile` 必需
- 图片 OCR：**本期不强制装 PaddleOCR/tesseract**。扫描件 PDF 走「PyMuPDF 渲染图片 → 调多模态模型」或先返回提示。如用户已装 `pytesseract`，则启用（见步骤 5 的降级链）。

> 把依赖同步写进 `requirements.txt`（若存在），三行：`pdfplumber`、`PyMuPDF`、`python-multipart`。

### 步骤 2：在 `utils/config.py` 追加配置

在文件末尾「健康检查配置」前后追加：

```python
# ==================== 简历解析配置 ====================
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads" / "resumes"))

RESUME_ANALYZE_CONFIG = {
    # 允许的文件扩展名
    "allowed_pdf_ext": {".pdf"},
    "allowed_image_ext": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
    # 单文件大小上限（字节），默认 10MB
    "max_file_size": int(os.getenv("RESUME_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
    # OCR 开关：装了 pytesseract 才会真正启用
    "ocr_enabled": os.getenv("RESUME_OCR_ENABLED", "true").lower() == "true",
    # LLM 任务类型（复用 MODEL_ROUTER；skill_extraction 用 glm-4，结构化输出能力好）
    "llm_task_type": os.getenv("RESUME_LLM_TASK_TYPE", "skill_extraction"),
    # 是否开启 JSON 模式
    "use_json_mode": os.getenv("RESUME_JSON_MODE", "true").lower() == "true",
}
```

### 步骤 3：在 `models/prompts.py` 追加简历解析模板

末尾追加（字段名严格对齐 `DATABASE_SCHEMA.md` + `LLM_RESUME_ANALYZE_API.md`）：

```python
# 简历解析 Prompt —— 严格 JSON 输出，字段对齐 DATABASE_SCHEMA.md 的 resumes + 子表
RESUME_PARSE_PROMPT = """你是一位专业的简历解析助手。请从以下简历文本中抽取结构化信息。
严格按 JSON 格式输出，不要包含任何多余文字、不要使用 Markdown 代码块。

抽取规则：
1. name: 姓名（必填，抽不到给 null）
2. gender: 性别，0=男 1=女（抽不到 null）
3. age: 年龄（整数，抽不到 null）
4. phone / email: 联系方式（抽不到 null）
5. city: 当前所在城市
6. work_years: 工作年限（整数）
7. education: 最高学历，取值之一：大专/本科/硕士/博士
8. expect_salary_min / expect_salary_max: 期望薪资上下限（元/月，整数）
9. expect_city: 期望工作城市
10. expect_job: 期望岗位
11. skills: 技能名称数组（中英文均可，如 ["Python","Docker","MySQL"]）
12. experiences: 工作经历数组，每项含 company_name(公司)、title(职位)、start_date(YYYY-MM-DD)、end_date(YYYY-MM-DD，在职则 null)、description(工作内容)、is_current(0/1)
13. educations: 教育经历数组，每项含 school(学校)、major(专业)、degree(学历)、start_date、end_date

输出 JSON 格式：
{{
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
  "skills": ["Python","Docker"],
  "experiences": [
    {{"company_name":"字节跳动","title":"后端工程师","start_date":"2022-06-01","end_date":"2024-08-01","description":"负责订单系统","is_current":0}}
  ],
  "educations": [
    {{"school":"浙江大学","major":"计算机科学与技术","degree":"本科","start_date":"2018-09-01","end_date":"2022-06-01"}}
  ]
}}

简历文本：
{resume_text}
"""
```

### 步骤 4：在 `models/schemas.py` 追加 Pydantic 模型

在文件末尾追加（用于响应校验 + 文档化）：

```python
# ==================== 简历解析 Schema ====================

class ResumeExperienceItem(BaseModel):
    """工作经历项（对齐 resume_experiences 表）"""
    company_name: str
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[int] = 0


class ResumeEducationItem(BaseModel):
    """教育经历项（对齐 resume_educations 表）"""
    school: str
    major: Optional[str] = None
    degree: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ParsedResumeData(BaseModel):
    """LLM 解析后的简历数据（对齐 LLM_RESUME_ANALYZE_API.md 第三节 + resumes 表）"""
    name: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    work_years: Optional[int] = None
    education: Optional[str] = None
    expect_salary_min: Optional[int] = None
    expect_salary_max: Optional[int] = None
    expect_city: Optional[str] = None
    expect_job: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experiences: List[ResumeExperienceItem] = Field(default_factory=list)
    educations: List[ResumeEducationItem] = Field(default_factory=list)
    parsed_raw: Optional[Dict[str, Any]] = None


class AnalyzeResumeRequest(BaseModel):
    """JSON 方式调用请求（传 file_url）"""
    file_url: str
    file_type: Optional[str] = None  # pdf / image，不传则按扩展名推断
```

### 步骤 5：新建 `core/resume_parser.py`（核心）

这是唯一新文件，负责「文件→文本」+「文本→结构化」两段。完整内容：

```python
"""
简历解析器 —— 文件(PDF/图片) → 文本 → LLM 结构化抽取

职责边界：
- 本模块只做「抽取」，不做「入库」（入库由 db_service 或调用方负责）。
- 对齐 check/LLM_RESUME_ANALYZE_API.md 的返回契约。
"""
import os
import json
from typing import Optional, Dict, Any, Tuple

from utils.config import RESUME_ANALYZE_CONFIG
from utils.logger import get_logger
logger = get_logger("core.resume_parser")


# ==================== 第一段：文件 → 文本 ====================

def _detect_file_type(file_url: str) -> str:
    """根据扩展名推断文件类型：pdf / image；不支持则抛 ValueError"""
    ext = os.path.splitext(file_url)[1].lower()
    if ext in RESUME_ANALYZE_CONFIG["allowed_pdf_ext"]:
        return "pdf"
    if ext in RESUME_ANALYZE_CONFIG["allowed_image_ext"]:
        return "image"
    raise ValueError(f"不支持的文件类型: {ext}")


def _extract_text_from_pdf(file_path: str) -> str:
    """PDF 文本提取：pdfplumber 主力，PyMuPDF 兜底"""
    text = ""
    # 1) pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        if text.strip():
            return text.strip()
    except ImportError:
        logger.warning("pdfplumber 未安装，尝试 PyMuPDF")
    except Exception as e:
        logger.warning(f"pdfplumber 提取失败: {e}")

    # 2) PyMuPDF 兜底（含扫描件渲染图片走 OCR）
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() or ""
        if text.strip():
            return text.strip()
        # 文本为空 → 可能是扫描件，渲染成图片走 OCR
        logger.info("PDF 无嵌入文字，疑似扫描件，尝试 OCR")
        return _ocr_pdf_pages(doc)
    except ImportError:
        raise RuntimeError("PDF 解析库未安装：需 pdfplumber 或 PyMuPDF")
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _ocr_image(file_path: str) -> str:
    """图片 OCR（需 pytesseract + Tesseract-OCR 可执行文件）"""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(file_path), lang="chi_sim+eng")
    except ImportError:
        raise RuntimeError("图片 OCR 需安装 pytesseract（pip install pytesseract）并配置 Tesseract-OCR")
    except Exception as e:
        raise RuntimeError(f"图片 OCR 失败: {e}")


def _ocr_pdf_pages(doc) -> str:
    """把 PDF 每页渲染成图片做 OCR（doc 为 fitz.Document）"""
    try:
        import pytesseract
        from PIL import Image
        import io
        text = ""
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text += pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text.strip()
    except ImportError:
        raise RuntimeError("扫描件 PDF 需 OCR，但 pytesseract 未安装")
    except Exception as e:
        raise RuntimeError(f"PDF OCR 失败: {e}")


def extract_resume_text(file_url: str, file_type: Optional[str] = None) -> Tuple[str, str]:
    """
    从文件提取文本。

    Args:
        file_url: 文件路径或 URL（本期支持本地路径；http URL 需调用方先下载到本地）
        file_type: pdf / image，不传则按扩展名推断

    Returns:
        (text, file_type)

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 类型不支持
        RuntimeError: 提取失败
    """
    if not os.path.exists(file_url):
        raise FileNotFoundError(f"文件不存在或无法读取: {file_url}")

    if not file_type:
        file_type = _detect_file_type(file_url)

    if file_type == "pdf":
        text = _extract_text_from_pdf(file_url)
    elif file_type == "image":
        text = _ocr_image(file_url)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")

    if not text or not text.strip():
        raise ValueError("简历内容为空")
    return text.strip(), file_type


# ==================== 第二段：文本 → 结构化（调 LLM） ====================

async def parse_resume_with_llm(resume_text: str) -> Dict[str, Any]:
    """
    调用 LLM 把简历文本抽成结构化 JSON。

    Returns:
        对齐 ParsedResumeData 的 dict；含 parsed_raw（LLM 原始返回）。
    """
    from models.prompts import RESUME_PARSE_PROMPT
    from services.llm_service import get_llm_service

    cfg = RESUME_ANALYZE_CONFIG
    prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text[:8000])  # 截断防超长

    llm = get_llm_service()
    response_format = {"type": "json_object"} if cfg["use_json_mode"] else None

    try:
        raw = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type=cfg["llm_task_type"],
            temperature=0.1,           # 结构化抽取用低温度
            max_tokens=4096,
            response_format=response_format,
        )
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}", exc_info=True)
        raise RuntimeError("简历分析服务异常")

    # 解析 JSON（兼容模型偶尔带 ```json 包裹）
    parsed = _safe_json_parse(raw)
    if parsed is None:
        raise RuntimeError("LLM 返回非合法 JSON，简历分析服务异常")

    # 字段兜底/归一
    parsed = _normalize_parsed(parsed)
    parsed["parsed_raw"] = parsed.get("parsed_raw") or {"raw_llm_output": raw}
    return parsed


def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """容错 JSON 解析：剥离 markdown 代码块、找首个 { 到末个 }"""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    try:
        return json.loads(s)
    except Exception:
        pass
    # 兜底：截取第一个 { 到最后一个 }
    lo, hi = s.find("{"), s.rfind("}")
    if 0 <= lo < hi:
        try:
            return json.loads(s[lo:hi + 1])
        except Exception:
            return None
    return None


def _normalize_parsed(data: Dict[str, Any]) -> Dict[str, Any]:
    """把 LLM 返回归一成 ParsedResumeData 兼容结构（缺字段补默认值）"""
    def opt_int(v):
        try:
            return int(v) if v not in (None, "") else None
        except Exception:
            return None

    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    return {
        "name": data.get("name"),
        "gender": opt_int(data.get("gender")),
        "age": opt_int(data.get("age")),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "city": data.get("city"),
        "work_years": opt_int(data.get("work_years")),
        "education": data.get("education"),
        "expect_salary_min": opt_int(data.get("expect_salary_min")),
        "expect_salary_max": opt_int(data.get("expect_salary_max")),
        "expect_city": data.get("expect_city"),
        "expect_job": data.get("expect_job"),
        "skills": skills,
        "experiences": data.get("experiences") or [],
        "educations": data.get("educations") or [],
        "parsed_raw": data.get("parsed_raw"),
    }


# ==================== 入口：文件 → 结构化 ====================

async def analyze_resume_file(file_url: str, file_type: Optional[str] = None) -> Dict[str, Any]:
    """完整流程：文件 → 文本 → LLM 结构化。返回 ParsedResumeData 兼容 dict。"""
    text, ftype = extract_resume_text(file_url, file_type)
    logger.info(f"简历文本提取完成: type={ftype}, chars={len(text)}")
    return await parse_resume_with_llm(text)
```

### 步骤 6：在 `api/agent_routes.py` 新增两个路由

在文件顶部 import 区追加：

```python
import os
import shutil
from fastapi import UploadFile, File, Form
from models.schemas import AnalyzeResumeRequest, ParsedResumeData
from core.resume_parser import analyze_resume_file, extract_resume_text
from utils.config import RESUME_ANALYZE_CONFIG, UPLOAD_DIR
```

在文件末尾（`create_evaluation` 路由之后）追加两个端点：

```python
# ==================== 简历解析 ====================

def _api_ok(data, message="解析成功", request_id="") -> dict:
    return {"code": 0, "message": message, "data": data,
            "request_id": request_id,
            "timestamp": __import__("datetime").datetime.now().isoformat()}


def _api_err(code: int, message: str, request_id="") -> dict:
    return {"code": code, "message": message, "data": None,
            "request_id": request_id,
            "timestamp": __import__("datetime").datetime.now().isoformat()}


@router.post("/analyze-resume")
async def analyze_resume(
    req: Request,
    payload: AnalyzeResumeRequest = None,
    file: UploadFile = File(None),
):
    """
    简历智能解析（对齐 LLM_RESUME_ANALYZE_API.md）

    两种调用方式（二选一）：
    1. multipart 上传文件：  curl -F file=@resume.pdf http://.../agents/analyze-resume
    2. JSON 传本地路径：     {"file_url": "/path/to/resume.pdf", "file_type": "pdf"}

    返回结构化字段；HTTP 始终 200，业务成败看 code。
    """
    request_id = req.headers.get("X-Request-ID", "")

    try:
        # —— 方式2：JSON 传 file_url ——
        if payload and payload.file_url:
            file_url = payload.file_url
            file_type = payload.file_type
        # —— 方式1：上传文件 ——
        elif file is not None:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            # 防路径穿越 + 保留扩展名
            import uuid
            ext = os.path.splitext(file.filename or "")[1].lower()
            saved_name = f"{uuid.uuid4().hex}{ext}"
            saved_path = os.path.join(UPLOAD_DIR, saved_name)
            with open(saved_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            file_url = saved_path
            file_type = None  # 让解析器按扩展名推断
        else:
            return _api_err(400, "未提供文件：请上传文件或传 file_url", request_id)

        data = await analyze_resume_file(file_url, file_type)
        return _api_ok(data, "解析成功", request_id)

    except FileNotFoundError as e:
        logger.error(f"简历文件读取失败: {e}")
        return _api_err(500, "文件不存在或无法读取", request_id)
    except ValueError as e:
        # 内容为空 或 类型不支持
        msg = str(e)
        code = 500 if "为空" in msg else 400
        logger.error(f"简历解析值错误: {msg}")
        return _api_err(code, msg, request_id)
    except RuntimeError as e:
        logger.error(f"简历解析服务异常: {e}", exc_info=True)
        return _api_err(500, str(e) or "简历分析服务异常", request_id)
    except Exception as e:
        logger.error(f"简历解析未知异常: {e}", exc_info=True)
        return _api_err(500, "简历分析服务异常", request_id)


@router.post("/analyze-resume-and-save")
async def analyze_resume_and_save(
    req: Request,
    user_id: int = Form(...),
    file: UploadFile = File(...),
):
    """
    解析 + 入库（联调用，便于验证字段正确写入 DATABASE_SCHEMA.md 的表）

    流程：上传文件 → LLM 抽取 → 写 resumes/resume_skills/resume_experiences/resume_educations
    返回 resume_id 及入库统计。
    """
    request_id = req.headers.get("X-Request-ID", "")
    try:
        # 1. 存文件
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        import uuid
        ext = os.path.splitext(file.filename or "")[1].lower()
        saved_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 2. 抽取
        data = await analyze_resume_file(saved_path)

        # 3. 入库
        from services.db_service import (
            get_db_service, ResumeEntity, ResumeSkillEntity,
            ResumeExperienceEntity, ResumeEducationEntity,
        )
        db = get_db_service()

        # 3.1 resumes 主表
        resume = ResumeEntity(
            user_id=user_id,
            name=data.get("name") or "未知",
            gender=data.get("gender"),
            age=data.get("age"),
            city=data.get("city") or "",
            phone=data.get("phone") or "",
            email=data.get("email") or "",
            source_type="pdf" if ext == ".pdf" else "image",
            file_url=saved_path,
            parse_status="done",
            work_years=data.get("work_years"),
            education=data.get("education") or "",
            expect_salary_min=data.get("expect_salary_min"),
            expect_salary_max=data.get("expect_salary_max"),
            expect_city=data.get("expect_city") or "",
            expect_job=data.get("expect_job") or "",
            parsed_raw=json.dumps(data.get("parsed_raw") or {}, ensure_ascii=False),
        )
        resume_id = db.create_resume(resume)

        # 3.2 resume_skills —— 抽取出的技能名做「字典型匹配」，
        #     已存在于 skills 表则关联 skill_id，不存在则新建技能字典项
        skill_ids = []
        for skill_name in data.get("skills", []):
            if not skill_name:
                continue
            # 先按 name 精确查
            existing = db.search_skills(keyword=skill_name, limit=50)
            matched = next((s for s in existing if s.get("name") == skill_name), None)
            if matched:
                skill_id = matched["id"]
            else:
                skill_id = db.create_skill(SkillEntity(name=skill_name, category=""))
            skill_ids.append(skill_id)
            db.create_resume_skill(ResumeSkillEntity(
                resume_id=resume_id, skill_id=skill_id, proficiency=3
            ))

        # 3.3 resume_experiences
        for exp in data.get("experiences", []):
            db.create_resume_experience(ResumeExperienceEntity(
                resume_id=resume_id,
                company_name=exp.get("company_name") or "未知公司",
                title=exp.get("title") or "",
                start_date=exp.get("start_date") or "",
                end_date=exp.get("end_date") or "",
                description=exp.get("description") or "",
                is_current=exp.get("is_current") or 0,
            ))

        # 3.4 resume_educations
        for edu in data.get("educations", []):
            db.create_resume_education(ResumeEducationEntity(
                resume_id=resume_id,
                school=edu.get("school") or "未知学校",
                major=edu.get("major") or "",
                degree=edu.get("degree") or "",
                start_date=edu.get("start_date") or "",
                end_date=edu.get("end_date") or "",
            ))

        return _api_ok({
            "resume_id": resume_id,
            "skill_count": len(skill_ids),
            "experience_count": len(data.get("experiences", [])),
            "education_count": len(data.get("educations", [])),
            "parsed": data,
        }, "解析并入库成功", request_id)

    except Exception as e:
        logger.error(f"解析入库失败: {e}", exc_info=True)
        # 失败时若已建 resume 记录，置 failed（简化：仅返回错误）
        return _api_err(500, f"简历分析服务异常: {e}", request_id)
```

> 注意：`analyze_resume_and_save` 里用到 `SkillEntity`，需在 import 处补：
> `from services.db_service import SkillEntity`（或在函数内 import，避免顶层循环依赖——上面已用函数内 import，故只需把 `SkillEntity` 一并加入那个 import 列表）。
> 同时顶部需 `import json`（`agent_routes.py` 当前未导入 json）。

### 步骤 7：依赖与 import 自检（落地时核对）

`api/agent_routes.py` 最终顶部需保证这些可用：

```python
import os
import json
import shutil
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel

from models.schemas import AnalyzeResumeRequest, ParsedResumeData  # ParsedResumeData 可选，仅文档用
from core.resume_parser import analyze_resume_file, extract_resume_text
from utils.config import RESUME_ANALYZE_CONFIG, UPLOAD_DIR
from utils.logger import get_logger
```

`analyze_resume_and_save` 函数内 import：

```python
from services.db_service import (
    get_db_service, ResumeEntity, ResumeSkillEntity,
    ResumeExperienceEntity, ResumeEducationEntity, SkillEntity,
)
```

---

## 四、验证步骤（对齐原 solve.md 第四节风格 + LLM_RESUME_ANALYZE_API.md 第六节联调）

1. **装依赖**：`pip install pdfplumber PyMuPDF python-multipart`
2. **启动服务**：
   ```bash
   # 强制走 SQLite（避开 MySQL）
   export DATABASE_URL="sqlite:///data/job_competency.db"
   export MYSQL_HOST=127.0.0.1 MYSQL_PORT=1 MYSQL_USER=x MYSQL_PASSWORD=x
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
   ```
3. **准备测试简历**：放一份 `test_resume.pdf` 到 `data/uploads/resumes/` 或任意路径
4. **方式 A：上传文件**：
   ```bash
   curl -X POST http://localhost:8001/agents/analyze-resume \
     -F "file=@data/uploads/resumes/test_resume.pdf"
   ```
   预期：`code=0`，`data` 含 name/skills/experiences/educations 等字段
5. **方式 B：JSON 传路径**：
   ```bash
   curl -X POST http://localhost:8001/agents/analyze-resume \
     -H "Content-Type: application/json" \
     -d '{"file_url":"data/uploads/resumes/test_resume.pdf","file_type":"pdf"}'
   ```
6. **入库版端点联调**（验证字段写对 `DATABASE_SCHEMA.md` 的表）：
   ```bash
   curl -X POST http://localhost:8001/agents/analyze-resume-and-save \
     -F "user_id=1" -F "file=@data/uploads/resumes/test_resume.pdf"
   ```
   然后用 db_service 验证：
   ```python
   db = get_db_service()
   print(db.get_resume(resume_id))                 # resumes 主表字段齐全
   print(db.get_resume_skills(resume_id))          # 关联技能
   print(db.get_resume_experiences(resume_id))     # 工作经历
   print(db.get_resume_educations(resume_id))      # 教育经历
   ```
7. **错误用例**：
   - 传不存在的路径 → `code=500, message="文件不存在或无法读取"`
   - 传 `.txt` → `code=400, message="不支持的文件类型: .txt"`
   - 传空内容 PDF → `code=500, message="简历内容为空"`
   - LLM key 未配置 → `code=500, message="简历分析服务异常"`

---

## 五、字段映射对照表（DATABASE_SCHEMA.md ↔ 接口返回 ↔ 表）

| 接口返回字段 | resumes 表列 | 说明 |
|------------|-------------|------|
| name | name | 姓名 |
| gender | gender | 0男1女 |
| age | age | 年龄 |
| phone | phone | 联系方式 |
| email | email | 邮箱 |
| city | city | 现居城市 |
| work_years | work_years | 工作年限 |
| education | education | 最高学历 |
| expect_salary_min/max | expect_salary_min/max | 期望薪资 |
| expect_city | expect_city | 期望城市 |
| expect_job | expect_job | 期望岗位 |
| parsed_raw | parsed_raw | LLM 原始返回(JSON) |
| skills | resume_skills(resume_id, skill_id) | 经字典匹配后关联 |
| experiences[] | resume_experiences | 直接写入 |
| educations[] | resume_educations | 直接写入 |
| — | parse_status | 由调用方置 `done`/`failed` |
| — | parse_error | 失败时由调用方记录 |

---

## 六、注意事项

1. **职责边界**：`/agents/analyze-resume` **只抽取返回**，不写库（严格遵守 `LLM_RESUME_ANALYZE_API.md` 第三节"归一化和入库由 JobHunter 负责"）。`/agents/analyze-resume-and-save` 是为本地联调额外提供，生产可下线。
2. **JSON 模式**：智谱 glm-4 支持 `response_format={"type":"json_object"}`，开启后输出合法 JSON 概率高；仍保留 `_safe_json_parse` 兜底剥离 markdown。
3. **PDF 扫描件**：pdfplumber/PyMuPDF 提不出文字时，自动走「渲染图片 → pytesseract OCR」。若环境未装 Tesseract，会抛 RuntimeError 提示安装，不静默返回空。
4. **文件安全**：上传文件名用 UUID 重命名，防路径穿越；大小限制 10MB（可配）。
5. **文本截断**：简历文本超 8000 字符截断，防 LLM token 超限。
6. **不破坏现有**：仅新增文件 + 在 `agent_routes.py` 末尾追加路由，`api/main.py` 无需改动（router 已挂载）。
7. **双库兼容**：本功能不直接写 SQL，全部走 db_service 的 CRUD 方法，MySQL/SQLite 自动兼容。
8. **LLM 依赖**：需配置有效的 `ZHIPU_API_KEY`（或 `LLM_API_KEY`），否则 LLM 调用会失败（返回 code=500）。健康检查 `/api/v1/health/ready` 的 `llm` 项可先行确认。

---

## 七、任务清单

- [ ] 步骤1：安装 pdfplumber / PyMuPDF / python-multipart，写入 requirements.txt
- [ ] 步骤2：utils/config.py 追加 UPLOAD_DIR、RESUME_ANALYZE_CONFIG
- [ ] 步骤3：models/prompts.py 追加 RESUME_PARSE_PROMPT
- [ ] 步骤4：models/schemas.py 追加 4 个 Pydantic 模型
- [ ] 步骤5：新建 core/resume_parser.py
- [ ] 步骤6：api/agent_routes.py 追加 analyze-resume / analyze-resume-and-save 路由
- [ ] 步骤7：import 自检（json/shutil/UploadFile/File/Form/SkillEntity）
- [ ] 第四节验证：curl 上传 PDF → 校验返回字段 → 入库版端点 → 校验四张表数据
