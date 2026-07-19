import uuid

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ParamError
from app.models import Resume

# 允许的文件类型(MIME 类型 -> 简历来源类型)
_ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
}


def _generate_resume_code() -> str:
    """生成简历编码。

    规律: R + 年月日(8位) + 当日秒数(5位补零) + 4位随机
        例: R20260628 + 45213 + a3f9 → "R2026062845213a3f9"

    和 user_code 思路一致: 带日期前缀方便识别, 加随机后缀防并发撞码。
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    second_part = f"{now.hour * 3600 + now.minute * 60 + now.second:05d}"
    rand_part = uuid.uuid4().hex[:4]
    return f"R{date_part}{second_part}{rand_part}"


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

    Args:
        title: 用户自定义的简历标题, 可不传, 为空时卡片会回退显示姓名

    Returns:
        新建的 Resume 对象(已 commit, 含 id)

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
    suffix = Path(file.filename).suffix.lower() # 取文件后缀，如1.pdf，就取.pdf
    # uuid.uuid4() 生成随机 UUID, 如 UUID('550e8400-e29b-41d4-a716-446655440000')
    # uuid.uuid4().hex 去掉横线,最后和后缀拼接起来
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / stored_name # 路径 uploads/resumes/xxx.pdf
    file_path.write_bytes(content) # 把字节内容写入文件

    # 数据库存的 URL: 相对路径(前端拼后端域名访问, 或以后挂 OSS)
    file_url = f"/uploads/resumes/{stored_name}"

    # ---------- 4. 建简历记录 ----------
    resume = Resume(
        resume_code=_generate_resume_code(),
        user_id=user_id,
        title=title.strip() if title else None,  # 用户自定义标题, 可空
        name="待解析",  # NOT NULL, 先占位, 解析后更新
        source_type=source_type,
        file_url=file_url,
        parse_status="pending",  # 默认 pending, 显式写出来更清晰
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)  # 拿到自增 id 和默认值

    return resume

async def get_all(db: AsyncSession, user_id: int) -> List[Resume]:
    """
    获取用户的卡片数据列表
    """
    stmt = select(Resume).where(Resume.user_id == user_id)
    resumes = (await db.scalars(stmt)).all()
    return resumes