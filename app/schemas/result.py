"""
统一返回结构 Result[T]

全站所有接口返回都用同一个壳子, 前端只需判断 code:

    {
        "code": 0,        // 0 = 成功, 非 0 = 业务错误码
        "message": "ok",   // 给前端展示的提示语
        "data": {...}      // 真正的业务数据, 失败时为 null
    }

配套:
    - BizCode:      业务码枚举(0=成功, 其余见注释)
    - Result:       泛型返回壳, 附 success/fail 等快捷构造
    - PageResult:   分页专用(在 schemas/page.py)
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.page import PageResult as _PageResult

# 业务数据的泛型, 允许 Result[UserOut] / Result[list[JobOut]] 这样用
T = TypeVar("T")


# ============================================================
# 业务码枚举
# ============================================================
class BizCode:
    """业务码常量。

    约定:
        0       = 成功
        1xx     = 通用错误(参数/权限/未登录)
        2xx     = 用户模块
        3xx     = 职位模块
        4xx     = 简历模块
        5xx     = 推荐模块
        9xxx    = 系统级异常(数据库/三方服务)

    用常量类而非 Enum 是为了直接当 int 用, 不用 .value, 代码更清爽。
    """

    # ---------- 通用 ----------
    SUCCESS = 0

    FAIL = 1                # 兜底的"操作失败"
    PARAM_ERROR = 100       # 参数校验不过(被 Pydantic 拦截的也会转成这个)
    UNAUTHORIZED = 101      # 未登录 / token 失效
    FORBIDDEN = 102         # 已登录但无权限
    NOT_FOUND = 103         # 资源不存在
    CONFLICT = 104          # 资源冲突(如手机号已注册)

    # ---------- 用户模块 ----------
    USER_NOT_EXIST = 200
    USER_PASSWORD_WRONG = 201
    USER_DISABLED = 202

    # ---------- 系统 ----------
    SYSTEM_ERROR = 9000     # 未预期的服务端异常


# ============================================================
# 统一返回结构
# ============================================================
class Result(BaseModel, Generic[T]):
    """所有接口的统一返回壳。

    路由里推荐写法:
        @router.get("/jobs/{job_id}", response_model=Result[JobOut])
        async def get_job(job_id: int):
            job = await ...
            return Result.success(job)

    前端约定:
        - HTTP 状态码恒为 200(除了 401/403/422 这种框架层的)
        - 业务成败完全看 code 字段
    """

    code: int = Field(
        default=BizCode.SUCCESS,
        description="业务码: 0=成功, 非 0 见 BizCode",
    )
    message: str = Field(
        default="ok",
        description="给用户看的提示语",
    )
    data: T | None = Field(
        default=None,
        description="业务数据, 失败时通常为 null",
    )

    # ---------- 快捷构造(成功) ----------
    @classmethod
    def success(cls, data: Any = None, message: str = "ok") -> "Result":
        """成功返回。data 可为 None(如 DELETE 接口)。"""
        return cls(code=BizCode.SUCCESS, message=message, data=data)

    @classmethod
    def success_page(
        cls,
        page_result: "_PageResult",
        message: str = "ok",
    ) -> "Result":
        """分页结果专用: 直接把 PageResult 塞进 data。"""
        return cls(code=BizCode.SUCCESS, message=message, data=page_result)

    # ---------- 快捷构造(失败) ----------
    @classmethod
    def fail(
        cls,
        message: str = "操作失败",
        code: int = BizCode.FAIL,
        data: Any = None,
    ) -> "Result":
        """失败返回。code 必须非 0。"""
        if code == BizCode.SUCCESS:
            raise ValueError("失败返回的 code 不能为 0, 请改用 Result.success()")
        return cls(code=code, message=message, data=data)


__all__ = ["BizCode", "Result", "T"]
