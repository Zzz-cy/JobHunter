"""业务异常定义。

路由 raise BizException → 全局异常处理器统一转成 Result JSON 返回前端。
"""
from app.schemas.result import BizCode


class BizException(Exception):
    """业务异常基类, 被全局处理器捕获后转成 Result.fail。"""

    def __init__(self, message: str = "操作失败", code: int = BizCode.FAIL):
        self.message = message
        self.code = code
        super().__init__(message)

    def __repr__(self) -> str:
        return f"BizException(code={self.code}, message={self.message!r})"



# 常用异常快捷工厂(让路由代码更短)
# 用法: raise NotFoundError("职位不存在")
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
