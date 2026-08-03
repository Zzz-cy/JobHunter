import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import httpx
from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ParamError
from app.models import Resume, ResumeExperience, ResumeEducation, ResumeSkill, Skill
from app.utils.codeUtil import generate_code

# 允许的文件类型(MIME 类型 -> 简历来源类型)
_ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
}



def _validate_file(file: UploadFile) -> str:
    """校验文件类型和大小, 返回 source_type('pdf' / 'image')。

    Raises:
        ParamError: 类型不允许 / 大小超限 / 文件名为空
    """
    # 1. 校验文件名(防止空文件名导致后续 .suffix 取不到)
    if not file.filename:
        raise ParamError("文件名为空")

    # 2. 校验类型(MIME 是浏览器传的, 相对可靠)
    source_type = _ALLOWED_TYPES.get(file.content_type)
    if not source_type:
        raise ParamError(
            f"不支持的文件类型: {file.content_type}, 仅支持 PDF/PNG/JPG"
        )

    # 3. 校验后缀名(双保险, 防止 content_type 被伪造)
    allowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_suffixes:
        raise ParamError(f"不支持的文件后缀: {suffix}")

    return source_type


async def save_resume_file(file: UploadFile, user_id: int, db: AsyncSession, title: str | None = None) -> Resume:
    """接收文件 + 存本地 + 建简历记录(状态 pending)。

    流程:
        1. 校验文件(类型/大小)
        2. 读文件内容到内存(校验大小)
        3. 生成唯一文件名, 写入 uploads/resumes/
        4. 在 resumes 表建记录(parse_status='pending', name 先填占位)
    title: 用户自定义的简历标题, 可不传, 为空时卡片会回退显示姓名
    Returns: 新建的 Resume 对象(已 commit, 含 id)
    Note:
        name 字段是 NOT NULL, 但上传时还没解析, 这里先填 "待解析",
        等 AI 解析完成后由后续步骤更新成真实姓名。
    """
    # ---------- 1. 校验 ----------
    source_type = _validate_file(file)

    # ---------- 2. 读内容 + 校验大小 ----------
    content = await file.read()
    max_bytes = settings.RESUME_MAX_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise ParamError(
            f"文件过大: {len(content) // 1024 // 1024}MB, "
            f"上限 {settings.RESUME_MAX_SIZE_MB}MB"
        )
    if len(content) == 0:
        raise ParamError("文件为空")

    # ---------- 3. 存文件 ----------
    # 目录: uploads/resumes/ (相对 backend/ 根目录)
    # 结果: Path("uploads/resumes")
    upload_dir = Path(settings.UPLOAD_DIR) / "resumes"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 文件名: uuid 防重名覆盖, 保留原后缀
    suffix = Path(file.filename).suffix.lower()  # 取文件后缀，如1.pdf，就取.pdf
    # uuid.uuid4() 生成随机 UUID, 如 UUID('550e8400-e29b-41d4-a716-446655440000')
    # uuid.uuid4().hex 去掉横线,最后和后缀拼接起来
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / stored_name  # 路径 uploads/resumes/xxx.pdf
    file_path.write_bytes(content)  # 把字节内容写入文件

    # 数据库存的 URL: 相对路径(前端拼后端域名访问, 或以后挂 OSS)
    file_url = f"/uploads/resumes/{stored_name}"

    # ---------- 4. 建简历记录 ----------
    # 如果是用户的第一份简历, 自动设为默认(is_primary=1)
    from sqlalchemy import func as _func
    existing_count = await db.scalar(
        select(_func.count()).select_from(Resume).where(
            Resume.user_id == user_id,
            Resume.is_deleted == 0,
        )
    )
    resume = Resume(
        resume_code=generate_code("R"),  # 统一用 codeUtil 生成(前缀 R + 日期 + 秒数 + 8位随机)
        user_id=user_id,
        title=title.strip() if title else None,  # 用户自定义标题, 可空
        name="待解析",  # NOT NULL, 先占位, 解析后更新
        source_type=source_type,
        file_url=file_url,
        parse_status="pending",  # 默认 pending, 显式写出来更清晰
        is_primary=1 if existing_count == 0 else 0,   # 第一份自动默认
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)  # 拿到自增 id 和默认值

    return resume


async def set_primary_resume(db: AsyncSession, user_id: int, resume_id: int) -> Resume:
    """设置默认简历(互斥: 先把该用户其他简历的 is_primary 清零, 再设当前这份)。

    Raises:
        NotFoundError: 简历不存在 / 不属于该用户 / 已删除
    """
    from app.core.exceptions import NotFoundError

    # 1. 校验: 简历存在 + 归属正确 + 未删除
    resume = await db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.is_deleted == 0,
        )
    )
    if not resume:
        raise NotFoundError("简历不存在或无权操作")

    # 2. 互斥清零: 该用户所有简历的 is_primary 全部置 0
    all_resumes = await db.scalars(
        select(Resume).where(
            Resume.user_id == user_id,
            Resume.is_deleted == 0,
        )
    )
    for r in all_resumes:
        r.is_primary = 0

    # 3. 把目标简历设为默认
    resume.is_primary = 1
    await db.commit()
    await db.refresh(resume)
    return resume


async def get_all(db: AsyncSession, user_id: int) -> List[Resume]:
    """
    获取用户的卡片数据列表
    """
    stmt = select(Resume).where(Resume.user_id == user_id,Resume.is_deleted == 0)
    resumes = (await db.scalars(stmt)).all()
    return resumes


# 简历 AI 解析，发请求给llm
async def call_llm_parse(file_path: str, resume_id: int, source_type: str) -> dict:
    """调队友的 LLM 服务, 把简历文件解析成 JSON。

    同机部署方案: 只传本地绝对路径给 LLM, LLM 自己 open() 读文件。
    不传文件二进制(省带宽), LLM 不直连数据库(职责分离)。
    """
    payload = {
        "file_url": file_path,  # 队友接口字段名是 file_url(传本地绝对路径)
        "file_type": source_type,  # pdf / image
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.LLM_SERVICE_URL}/agents/analyze-resume",
                json=payload,
                timeout=settings.LLM_PARSE_TIMEOUT,
            )
            resp.raise_for_status()
    except httpx.ConnectError:
        raise ParamError("简历解析服务不可达(未启动?)")
    except httpx.TimeoutException:
        raise ParamError("简历解析超时, 请重试")

    result = resp.json()
    # 约定 LLM 也返回 Result{code, message, data} 格式
    if result.get("code") != 0:
        raise ParamError(result.get("message") or "简历解析失败")
    return result.get("data") or {}


# 技能字典归一化
async def find_skill_by_name(db: AsyncSession, name: str) -> Skill | None:
    """在 skills 字典表查技能, 支持别名归一。

    LLM 抽取的可能是 "Python3" "Py" 等别名, 要映射到标准技能。
    匹配优先级: 标准名 > alias 字段(逗号分隔)。
    """
    if not name:
        return None
    name_lower = name.lower().strip()
    stmt = select(Skill).where(
        or_(
            func.lower(Skill.name) == name_lower,
            # alias 存的是 "py,python3,python3.x" 这种逗号分隔字符串
            func.lower(Skill.alias).like(f"%{name_lower}%"),
        )
    )
    return await db.scalar(stmt)


# 数据入库
async def save_parsed_result(db: AsyncSession, resume_id: int, parsed: dict) -> None:
    """把 LLM 返回的 JSON 拆开存到 4 张表。

    - resumes 主表: 存 name/age/phone 等单值字段
    - resume_experiences: 存工作经历(一对多)
    - resume_educations: 存教育经历(一对多)
    - resume_skills: 存技能(需查字典表归一)

    注意: 原始 JSON 也存一份到 parsed_raw 字段, 便于调试回溯。
    """
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise ParamError(f"简历不存在: id={resume_id}")

    # ---------- 1. 存主表(单值字段) ----------
    resume.name = parsed.get("name") or "未识别"
    resume.gender = parsed.get("gender")
    resume.age = parsed.get("age")
    resume.phone = parsed.get("phone")
    resume.email = parsed.get("email")
    resume.city = parsed.get("city")
    resume.work_years = parsed.get("work_years")
    resume.education = parsed.get("education")
    # 原始 JSON 存一份(调试/审计/以后重新归一用)
    resume.parsed_raw = parsed

    # ---------- 2. 存工作经历(一对多) ----------
    # 注意: 队友 LLM 返回的字段是 company_name(不是 company)
    for exp in parsed.get("experiences", []):
        db.add(ResumeExperience(
            resume_id=resume_id,
            company_name=exp.get("company_name") or exp.get("company") or "未知公司",
            title=exp.get("title"),
            description=exp.get("description"),
        ))

    # ---------- 3. 存教育经历(一对多) ----------
    for edu in parsed.get("educations", []):
        db.add(ResumeEducation(
            resume_id=resume_id,
            school=edu.get("school", "未知学校"),
            major=edu.get("major"),
            degree=edu.get("degree"),
        ))

    # ---------- 4. 存技能(需查字典表归一) ----------
    # LLM 只返回技能名数组, 这里负责映射到标准 skill_id
    for skill_name in parsed.get("skills", []):
        skill = await find_skill_by_name(db, skill_name)
        if skill:
            db.add(ResumeSkill(resume_id=resume_id, skill_id=skill.id))
        # 字典表没有的技能: 暂时跳过(以后扩充字典)


# 完整解析流程: 调 LLM + 拆 JSON + 存 4 张表 + 更新状态机
async def parse_and_save_resume(db: AsyncSession, resume_id: int) -> Resume:
    """完整解析流程: 调 LLM + 拆 JSON + 存 4 张表 + 更新状态机。

    状态流转: pending → parsing → done / failed

    使用场景:
        上传成功后立即调用(同步等待 LLM 返回)。
        或以后改成 BackgroundTask(异步, 前端轮询状态)。
    """
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise ParamError(f"简历不存在: id={resume_id}")

    # 1. 状态 → parsing
    resume.parse_status = "parsing"
    await db.commit()

    try:
        # 2. 文件绝对路径
        rel_path = resume.file_url.lstrip("/")
        abs_path = str(Path(settings.UPLOAD_DIR).resolve().parent / rel_path)
        # backend/uploads/resumes/xxx.pdf

        # 3. 调 LLM 解析
        parsed_json = await call_llm_parse(
            file_path=abs_path,
            resume_id=resume_id,
            source_type=resume.source_type,
        )

        # 4. 拆 JSON 存 4 张表
        await save_parsed_result(db, resume_id, parsed_json)

        # 5. 状态 → done
        resume.parse_status = "done"
        resume.parse_error = None
        await db.commit()

    except Exception as e:
        # 解析失败: 记录原因 + 状态 → failed(不影响上传)
        resume.parse_status = "failed"
        resume.parse_error = str(e)[:500]
        await db.commit()

    await db.refresh(resume)
    return resume
