"""统一返回壳 Result[T]。

全站接口返回统一为 {code, message, data}, 前端只判断 code。
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.page import PageResult as _PageResult

# 业务数据的泛型, 允许 Result[UserOut] / Result[list[JobOut]] 这样用
T = TypeVar("T")


# 业务码枚举
class BizCode:
    """业务码常量(0=成功, 1xx 通用, 2xx 用户, 9xxx 系统)。用类不用 Enum, 直接当 int 用。"""

    # 通用
    SUCCESS = 0

    FAIL = 1                # 兜底的"操作失败"
    PARAM_ERROR = 100       # 参数校验不过(被 Pydantic 拦截的也会转成这个)
    UNAUTHORIZED = 101      # 未登录 / token 失效
    FORBIDDEN = 102         # 已登录但无权限
    NOT_FOUND = 103         # 资源不存在
    CONFLICT = 104          # 资源冲突(如手机号已注册)

    # 用户模块
    USER_NOT_EXIST = 200
    USER_PASSWORD_WRONG = 201
    USER_DISABLED = 202

    # 系统
    SYSTEM_ERROR = 9000     # 未预期的服务端异常


# 统一返回结构
class Result(BaseModel, Generic[T]):
    """所有接口的统一返回壳。HTTP 恒 200(框架层错误除外), 业务成败看 code。"""

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

    # 快捷构造(成功)
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

    # 快捷构造(失败)
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
