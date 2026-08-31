"""全局异常处理器: 把异常统一转成 Result JSON 返回。

BizException → 自带 code/message; 参数校验错 → PARAM_ERROR; 兜底 → SYSTEM_ERROR(隐藏堆栈)。
"""
import logging
import sys

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import BizException
from app.schemas.result import BizCode, Result

logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册所有全局异常处理器到 app。
    """

    # 业务异常: 用自带 code/message
    @app.exception_handler(BizException)
    async def handle_biz_exception(_: Request, exc: BizException):
        # 业务异常是"预期内的错误", 不用记日志
        return JSONResponse(
            status_code=status.HTTP_200_OK,   # HTTP 恒 200, 业务成败看 code
            content=Result.fail(exc.message, code=exc.code).model_dump(),
        )

    # 参数校验失败: Pydantic 拦截的 422
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        first_msg = errors[0]["msg"] if errors else "参数错误"
        logger.info(f"参数校验失败: {errors}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,   # 也转成 200, 统一格式
            content=Result.fail(
                f"参数错误: {first_msg}", code=BizCode.PARAM_ERROR,
            ).model_dump(),
        )

    # 兜底: 未预期的异常(500)
    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception):
        # 这种是 bug, 必须记完整堆栈, 方便排查
        logger.exception(f"未预期异常: {exc}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=Result.fail(
                "服务器内部错误, 请稍后重试",
                code=BizCode.SYSTEM_ERROR,
            ).model_dump(),
            # 生产环境不把 exc 详情返回前端(安全)
        )
