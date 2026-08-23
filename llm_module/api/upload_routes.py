"""
Agent resume upload routes.

These endpoints require python-multipart (UploadFile/Form).
Kept separate from the core agent router so a missing dependency
cannot prevent /agents/chat and other core routes from registering.
"""
import json
import os
import shutil
from typing import Optional

from fastapi import APIRouter, Request, UploadFile, File, Form

from utils.logger import get_logger

logger = get_logger("api.upload_routes")

router = APIRouter(prefix="/agents", tags=["Agent-upload"])


# ==================== 简历解析 ====================

def _api_ok(data, message="解析成功", request_id="") -> dict:
    """构建简历解析成功响应（对齐 LLM_RESUME_ANALYZE_API.md 第四节：HTTP 始终 200）"""
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": request_id,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


def _api_err(code: int, message: str, request_id="") -> dict:
    """构建简历解析失败响应"""
    return {
        "code": code,
        "message": message,
        "data": None,
        "request_id": request_id,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


@router.post("/analyze-resume")
async def analyze_resume(
    req: Request,
    file: Optional[UploadFile] = File(None),
    file_url: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None),
):
    """
    简历智能解析（对齐 LLM_RESUME_ANALYZE_API.md）

    三种调用方式（三选一）：
    1. multipart 上传文件：  curl -F file=@resume.pdf http://.../agents/analyze-resume
    2. multipart 传本地路径：curl -F file_url=/path/to/resume.pdf http://.../agents/analyze-resume
    3. JSON body 传路径：    curl -H Content-Type:application/json -d '{"file_url":"..."}' http://.../agents/analyze-resume

    返回结构化字段；HTTP 始终 200，业务成败看 code。
    """
    from core.resume_parser import analyze_resume_file
    from utils.config import UPLOAD_DIR, RESUME_ANALYZE_CONFIG

    request_id = req.headers.get("X-Request-ID", "")

    try:
        actual_file_url = None
        actual_file_type = file_type
        saved_path = None

        # —— 方式3：JSON body ——
        if file is None and file_url is None:
            ct = (req.headers.get("content-type") or "")
            if "application/json" in ct:
                try:
                    body = await req.json()
                    file_url = body.get("file_url")
                    file_type = body.get("file_type") or file_type
                except Exception:
                    pass

        # —— 方式1：上传文件 ——
        if file is not None:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            # 防路径穿越 + 保留扩展名
            import uuid
            ext = os.path.splitext(file.filename or "")[1].lower()
            allowed = RESUME_ANALYZE_CONFIG["allowed_pdf_ext"] | RESUME_ANALYZE_CONFIG["allowed_image_ext"]
            if ext not in allowed:
                return _api_err(400, f"不支持的文件类型: {ext}", request_id)
            saved_name = f"{uuid.uuid4().hex}{ext}"
            saved_path = os.path.join(UPLOAD_DIR, saved_name)
            with open(saved_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            actual_file_url = saved_path
            actual_file_type = None  # 让解析器按扩展名推断

        # —— 方式2：JSON/表单传 file_url ——
        elif file_url:
            actual_file_url = file_url
            saved_path = None
        else:
            return _api_err(400, "未提供文件：请上传文件(file)或传 file_url", request_id)

        data = await analyze_resume_file(actual_file_url, actual_file_type)
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
    from core.resume_parser import analyze_resume_file
    from utils.config import UPLOAD_DIR

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
            ResumeExperienceEntity, ResumeEducationEntity, SkillEntity,
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

        # 3.2 resume_skills —— 抽取出的技能名做「字典型匹配」
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
        return _api_err(500, f"简历分析服务异常: {e}", request_id)

