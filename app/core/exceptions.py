"""
业务异常定义

设计思想:
    "错误就该用异常表达"(raise), 但又要保持全站统一 Result 返回格式。
    解决方案: 定义业务异常类, 用全局异常处理器把它转成 Result JSON。

    路由代码:    raise BizException("用户已存在", code=BizCode.CONFLICT)
                         ↓ FastAPI 捕获异常
    异常处理器:  把 BizException 转成 Result.fail(...).model_dump()
                         ↓
    前端收到:    {"code": 104, "message": "用户已存在", "data": null}   ← 统一格式!
"""
from app.schemas.result import BizCode


class BizException(Exception):
    """业务异常基类。

    所有业务错误(用户已存在/职位不存在/权限不足...)都抛这个或它的子类。
    全局异常处理器(exception_handlers.py)会捕获它, 转成统一 Result 格式。

    Args:
        message: 给前端展示的错误提示
        code:    业务码(见 BizCode), 默认 FAIL=1
    """

    def __init__(self, message: str = "操作失败", code: int = BizCode.FAIL):
        self.message = message
        self.code = code
        super().__init__(message)

    def __repr__(self) -> str:
        return f"BizException(code={self.code}, message={self.message!r})"


# ============================================================
# 常用异常快捷工厂(让路由代码更短)
# 用法: raise NotFoundError("职位不存在")
#       raise ConflictError("用户已存在")
# ============================================================
class NotFoundError(BizException):
    """资源不存在(404 业务码)。"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=BizCode.NOT_FOUND)


class ConflictError(BizException):
    """资源冲突(如手机号已注册)。"""

    def __init__(self, message: str = "资源已存在"):
        super().__init__(message, code=BizCode.CONFLICT)


class UnauthorizedError(BizException):
    """未登录 / token 失效。"""

    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(message, code=BizCode.UNAUTHORIZED)


class ForbiddenError(BizException):
    """已登录但无权限。"""

    def __init__(self, message: str = "无权限访问"):
        super().__init__(message, code=BizCode.FORBIDDEN)


class ParamError(BizException):
    """参数错误(业务层面的, 非 Pydantic 校验)。"""

    def __init__(self, message: str = "参数错误"):
        super().__init__(message, code=BizCode.PARAM_ERROR)
