# 岗能智绘 - LLM Module Dockerfile
# 多阶段构建：基础镜像 → 依赖安装 → 运行时

FROM docker.1ms.run/library/python:3.11-slim AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 依赖安装阶段
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行时阶段
FROM base AS runtime

# 复制已安装的依赖
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/persist /app/data/export /app/data/vector_db /app/logs

# 暴露端口
EXPOSE 8001

# 健康检查(服务实际监听 8001, 原来误写 5173 导致永远 unhealthy)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/v1/health/live')" || exit 1

# 启动命令
CMD ["python", "-m", "api.main"]
