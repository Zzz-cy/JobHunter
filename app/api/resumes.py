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
from app.services.resumes_service import save_resume_file, get_all, parse_and_save_resume, set_primary_resume
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
    """上传简历文件 + 同步触发 AI 解析。

    流程:
      1. 校验 + 存文件 + 建 resume 记录(status=pending)
      2. 调队友 LLM 解析(同步等待, 可能 10-30 秒)
      3. 拆 JSON 存 4 张表, 更新 status=done
      4. 失败则 status=failed(不影响上传, 前端能看到状态)

    解析失败时:
      - resume 记录已建好(file 还在), 用户可重新解析
      - 前端根据 parse_status 判断显示结果还是错误
    """
    # 1. 存文件 + 建记录
    resume = await save_resume_file(file, current_user.id, db, title=title)
    # 2. 同步调 LLM 解析(失败不影响返回, status 会变 failed)
    resume = await parse_and_save_resume(db, resume.id)
    out = ResumeUploadOut.model_validate(resume)
    message = "上传并解析成功" if resume.parse_status == "done" else "上传成功, 但解析失败"
    return Result.success(data=out, message=message)

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


@router.post("/{resume_id}/reparse", response_model=Result[ResumeUploadOut], summary="重新解析简历")
async def reparse_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # 校验简历归属(防止用户解析别人的简历)
    resume = await db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    if resume is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("简历不存在或无权操作")

    resume = await parse_and_save_resume(db, resume.id)
    out = ResumeUploadOut.model_validate(resume)
    message = "重新解析成功" if resume.parse_status == "done" else "重新解析失败, 请稍后重试"
    return Result.success(data=out, message=message)

@router.put("/{resume_id}/primary", response_model=Result, summary="设为默认简历")
async def set_primary(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """设为默认简历(互斥: 该用户其他简历自动取消默认)。"""
    await set_primary_resume(db, current_user.id, resume_id)
    return Result.success(message="已设为默认简历")

@router.delete("/{resume_id}", response_model=Result, summary="删除简历")
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    resume = await db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,   # 校验归属, 防越权删除
            Resume.is_deleted == 0,
        )
    )
    if resume is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("简历不存在或无权操作")

    resume.is_deleted = 1   # 软删除
    await db.commit()
    return Result.success(message="删除成功")
