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
            doc.close()
            return text.strip()
        # 文本为空 → 可能是扫描件，渲染成图片走 OCR
        logger.info("PDF 无嵌入文字，疑似扫描件，尝试 OCR")
        result = _ocr_pdf_pages(doc)
        doc.close()
        return result
    except ImportError:
        raise RuntimeError("PDF 解析库未安装：需 pdfplumber 或 PyMuPDF")


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
    """把 LLM 返回归一成 ParsedResumeData 兼容结构（缺字段补默认值，过滤非法元素）"""
    def opt_int(v):
        try:
            return int(v) if v not in (None, "") else None
        except Exception:
            return None

    def opt_str(v):
        """保证字符串字段不为 None，统一转为 str 或空串"""
        if v is None:
            return None
        return str(v) if v != "" else None

    # skills：过滤 None、非 str、空串
    raw_skills = data.get("skills") or []
    if isinstance(raw_skills, str):
        raw_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    skills = [s for s in raw_skills if isinstance(s, str) and s.strip()]

    # experiences：过滤 None、非 dict；子字段兜底
    raw_exps = data.get("experiences") or []
    experiences = []
    for exp in raw_exps:
        if not isinstance(exp, dict):
            continue
        experiences.append({
            "company_name": str(exp.get("company_name") or ""),
            "title": exp.get("title") or None,
            "start_date": exp.get("start_date") or None,
            "end_date": exp.get("end_date") or None,
            "description": exp.get("description") or None,
            "is_current": opt_int(exp.get("is_current")),
        })

    # educations：过滤 None、非 dict；子字段兜底
    raw_edus = data.get("educations") or []
    educations = []
    for edu in raw_edus:
        if not isinstance(edu, dict):
            continue
        educations.append({
            "school": str(edu.get("school") or ""),
            "major": edu.get("major") or None,
            "degree": edu.get("degree") or None,
            "start_date": edu.get("start_date") or None,
            "end_date": edu.get("end_date") or None,
        })

    return {
        "name": opt_str(data.get("name")),
        "gender": opt_int(data.get("gender")),
        "age": opt_int(data.get("age")),
        "phone": opt_str(data.get("phone")),
        "email": opt_str(data.get("email")),
        "city": opt_str(data.get("city")),
        "work_years": opt_int(data.get("work_years")),
        "education": opt_str(data.get("education")),
        "expect_salary_min": opt_int(data.get("expect_salary_min")),
        "expect_salary_max": opt_int(data.get("expect_salary_max")),
        "expect_city": opt_str(data.get("expect_city")),
        "expect_job": opt_str(data.get("expect_job")),
        "skills": skills,
        "experiences": experiences,
        "educations": educations,
        "parsed_raw": data.get("parsed_raw"),
    }


# ==================== 入口：文件 → 结构化 ====================

async def analyze_resume_file(file_url: str, file_type: Optional[str] = None) -> Dict[str, Any]:
    """完整流程：文件 → 文本 → LLM 结构化。返回 ParsedResumeData 兼容 dict。"""
    text, ftype = extract_resume_text(file_url, file_type)
    logger.info(f"简历文本提取完成: type={ftype}, chars={len(text)}")
    return await parse_resume_with_llm(text)
