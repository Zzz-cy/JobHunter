# 后端镜像: FastAPI 主服务(8000)
# docker.1ms.run 国内代理(compose 里的 mysql/neo4j 走它已验证可用)
FROM docker.1ms.run/library/python:3.12-slim

WORKDIR /app

# 先装依赖(利用 docker 层缓存: 只有 requirements 变了才重装)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 代码 + SQL 脚本(bootstrap 初始化要读 db/mysql/*.sql)
COPY app ./app
COPY scripts ./scripts
COPY db ./db
COPY run.py .

EXPOSE 8000
CMD ["python", "run.py"]
