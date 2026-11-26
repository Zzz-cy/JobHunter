"""账号管理接口(仅管理员): 用户列表 / 设为收回管理员 / 封禁解封。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.schemas import (
    AdminUserOut,
    AdminUserQuery,
    AdminUserRoleSchema,
    AdminUserStatusSchema,
    PageResult,
    Result,
)
from app.services.user_service import query_admin_users, set_user_role, set_user_status
from app.utils.jwtUtil import require_admin

router = APIRouter(prefix="/admin/users", tags=["账号管理(管理员)"])


@router.get("", response_model=Result[PageResult[AdminUserOut]], summary="用户分页列表(管理员)")
async def list_users(
        params: AdminUserQuery = Depends(),
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
):
    """昵称/手机号模糊搜索 + 分页; 只返回未软删除账号。"""
    users, total = await query_admin_users(params, db)
    page_result = PageResult(
        items=[AdminUserOut.model_validate(u) for u in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )
    return Result.success_page(page_result)


@router.put("/{user_id}/role", response_model=Result, summary="设为/收回管理员(管理员)")
async def change_user_role(
        user_id: int,
        data: AdminUserRoleSchema,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin),
):
    """不能操作自己; 已是目标角色时幂等返回成功。"""
    await set_user_role(user_id, data.role, db, current_user.id)
    message = "已设为管理员" if data.role == "admin" else "已收回管理员权限"
    return Result.success(message=message)


@router.put("/{user_id}/status", response_model=Result, summary="封禁/解封账号(管理员)")
async def change_user_status(
        user_id: int,
        data: AdminUserStatusSchema,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin),
):
    """不能操作自己; 封禁后登录被拒且在线会话下一次请求即失效。"""
    await set_user_status(user_id, data.status, db, current_user.id)
    message = "账号已封禁" if data.status == "banned" else "账号已解封"
    return Result.success(message=message)
