"""
JobHunter 存储初始化脚本

用法:
    python backend/scripts/init_storage.py

会执行：
    1. 创建 MySQL 数据库 + 表 (01_schema.sql)
    2. 写入字典和测试账号 (02_seed.sql)
    3. 写入假数据用于前端调试 (03_mock_data.sql)
    # 4. 创建 ES 索引(jobs / resumes / companies)  # 暂时注释,等需要时再启用

依赖:
    pip install pymysql
    # pip install elasticsearch==8.*  # ES 暂时不用
"""
from __future__ import annotations

import os
from pathlib import Path

import pymysql

# 路径:本脚本在 backend/scripts/,数据库文件在 backend/db/
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DB_DIR = BASE_DIR / "db"

# ---- 配置(可从 .env 读取,这里给本地默认值) ----
MYSQL_CONF = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
}
# ES_URL = os.getenv("ES_URL", "http://127.0.0.1:9200")

MYSQL_SCRIPTS = ["01_schema.sql", "02_seed.sql", "03_mock_data.sql"]
# ES 暂时不用,等接入全文检索时再启用
# ES_INDICES = ["jobs_index.json", "resumes_index.json", "companies_index.json"]
# ES_INDEX_NAMES = {"jobs_index.json": "jobs", "resumes_index.json": "resumes", "companies_index.json": "companies"}


def split_sql(sql_text: str) -> list[str]:
    """按分号切分 SQL,先剔除行注释,避免 INSERT 被前导 -- 误过滤"""
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    text = "\n".join(lines)
    return [s.strip() for s in text.split(";") if s.strip()]


def init_mysql() -> None:
    print("==> [MySQL] 开始初始化...")
    conn = pymysql.connect(**MYSQL_CONF, charset="utf8mb4", autocommit=True)
    try:
        with conn.cursor() as cur:
            # 确保有数据库上下文(03_mock_data.sql 顶部也有 USE)
            cur.execute("CREATE DATABASE IF NOT EXISTS jobhunter "
                        "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci")
            cur.execute("USE jobhunter")
            for script in MYSQL_SCRIPTS:
                sql = (DB_DIR / "mysql" / script).read_text(encoding="utf-8")
                for stmt in split_sql(sql):
                    # 跳过脚本里再次出现的 USE(上面已选库,重复无害但冗余)
                    if stmt.upper().startswith("USE "):
                        continue
                    cur.execute(stmt)
                print(f"   ✓ executed {script}")
    finally:
        conn.close()
    print("==> [MySQL] 完成\n")


# ES 暂时不用,等接入全文检索时取消下方注释
# def init_es() -> None:
#     from elasticsearch import Elasticsearch
#     import json
#     import sys
#     print("==> [ES] 开始初始化...")
#     es = Elasticsearch(ES_URL)
#     if not es.info():
#         print("   ✗ 无法连接 ES")
#         sys.exit(1)
#     for fname in ES_INDICES:
#         index_name = ES_INDEX_NAMES[fname]
#         body = json.loads((DB_DIR / "es" / fname).read_text(encoding="utf-8"))
#         if es.indices.exists(index=index_name):
#             print(f"   · {index_name} 已存在，跳过")
#             continue
#         es.indices.create(index=index_name, **body)
#         print(f"   ✓ created index: {index_name}")
#     print("==> [ES] 完成\n")


if __name__ == "__main__":
    try:
        init_mysql()
    except Exception as e:
        print(f"[MySQL] 初始化失败: {e}")
    # ES 暂时不用
    # try:
    #     init_es()
    # except Exception as e:
    #     print(f"[ES] 初始化失败: {e}")
    print("全部完成。")
