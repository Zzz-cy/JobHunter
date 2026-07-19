from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Resume
from app.schemas import Result
from app.schemas.resumes import ResumeUploadOut, OutList
from app.services.resumes_service import save_resume_file, get_all
from app.utils.jwtUtil import get_current_user

router = APIRouter(prefix="/resumes", tags=["简历"])

@router.post("/upload", response_model=Result[ResumeUploadOut], summary="上传简历")
async def upload_resume(
    # File(...) 标记这是文件上传字段(multipart/form-data), 不是 JSON，前端上传时必须用 FormData, 这个参数从 multipart/form-data 表单里取
    file: UploadFile = File(..., description="简历文件(PDF/PNG/JPG)"),
    # title 跟 file 在同一个 multipart 表单里, 前端 formData.append('title', xxx)
    title: str | None = Form(None, description="用户自定义简历标题, 可不传"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),   # 上传简历必须登录
):
    """上传简历文件。

    - 只接收 PDF/PNG/JPG
    - 大小上限 10MB(可配)
    - 上传成功后返回 resume_id, 状态为 pending(待解析)
    - 解析是异步的, 前端用 resume_id 轮询 /resumes/{id} 查状态
      (轮询接口第 2 步再做)
    """
    resume = await save_resume_file(file, current_user.id, db, title=title)
    out = ResumeUploadOut.model_validate(resume)
    return Result.success(data=out, message="上传成功, 正在解析")

@router.get("/all", response_model=Result[list[OutList]], summary="简历查询")
async def get_all_resumes(db: AsyncSession = Depends(get_db),current_user=Depends(get_current_user)):
    resumes = await get_all(db, current_user.id)
    data = [OutList.model_validate(r) for r in resumes]
    return Result.success(data=data, message="查询成功")


# MIME 类型映射(浏览器好识别, 决定是预览还是下载)
_MIME_MAP = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


@router.get("/{resume_id}/file", summary="下载/预览简历原文件")
async def get_resume_file(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """返回简历原文件(PDF/PNG/JPG)。

    鉴权: 只允许 resume 的所有者访问, 避免文件被其他用户(或未登录用户)通过 URL 拿到。
    替代了之前直接 mount 的 /uploads/ 公开静态路由。
    """
    # 1. 查简历记录(确认存在 + 确认归属)
    resume = await db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    if resume is None or not resume.file_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在或无权访问")

    # 2. file_url 形如 "/uploads/resumes/xxx.pdf", 拼出磁盘真实路径
    #    settings.UPLOAD_DIR 是相对 backend/ 的目录, 取相对于 cwd 解析
    rel_path = resume.file_url.lstrip("/")
    # 去掉前缀 "uploads/" 后拼到 UPLOAD_DIR 下(防止 file_url 前缀写死导致路径拼接错位)
    if rel_path.startswith(f"{settings.UPLOAD_DIR}/"):
        rel_path = rel_path[len(settings.UPLOAD_DIR) + 1:]
    file_path = Path(settings.UPLOAD_DIR) / rel_path

    # 3. 防目录穿越 + 文件存在性检查
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    media_type = _MIME_MAP.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, filename=resume.title or file_path.name)
