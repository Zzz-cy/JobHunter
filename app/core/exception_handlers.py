"""
全局异常处理器

作用: 把各种异常"翻译"成统一的 Result JSON, 前端永远收到统一格式,
      不用区分"成功响应"和"错误响应"的解析逻辑。

注册方式: 在 main.py 调用 register_exception_handlers(app)

处理的异常类型:
    1. BizException 及其子类:  用异常自带的 code/message 转 Result.fail
    2. RequestValidationError:  Pydantic 参数校验失败, 转 code=PARAM_ERROR
    3. Exception(兜底):        未预期的异常, 转 code=SYSTEM_ERROR, 隐藏堆栈

返回格式(前端永远收到这个壳子):
    {"code": 非零, "message": "提示", "data": null}
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import BizException
from app.schemas.result import BizCode, Result

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册所有全局异常处理器到 app。

    在 main.py 里调用一次即可, 之后所有路由抛出的异常都会被这里捕获处理。
    """

    # ---------- 1. 业务异常: 用自带 code/message ----------
    @app.exception_handler(BizException)
    async def handle_biz_exception(_: Request, exc: BizException):
        # 业务异常是"预期内的错误", 不用记日志
        return JSONResponse(
            status_code=status.HTTP_200_OK,   # HTTP 恒 200, 业务成败看 code
            content=Result.fail(exc.message, code=exc.code).model_dump(),
        )

    # ---------- 2. 参数校验失败: Pydantic 拦截的 422 ----------
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        # 把 Pydantic 的详细错误收起来, 只给前端一个友好提示
        # (详细信息太技术, 暴露给用户不友好; 调试时看服务端日志)
        errors = exc.errors()
        first_msg = errors[0]["msg"] if errors else "参数错误"
        logger.info(f"参数校验失败: {errors}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,   # 也转成 200, 统一格式
            content=Result.fail(
                f"参数错误: {first_msg}", code=BizCode.PARAM_ERROR,
            ).model_dump(),
        )

    # ---------- 3. 兜底: 未预期的异常(500) ----------
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
