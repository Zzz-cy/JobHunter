"""存储初始化脚本: 建库建表 + 字典种子 + 假数据。

用法: python -m scripts.init_storage
"""
from __future__ import annotations

import os
from pathlib import Path

import pymysql

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DB_DIR = BASE_DIR / "db"

MYSQL_CONF = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
}

MYSQL_SCRIPTS = ["01_schema.sql", "02_seed.sql", "03_mock_data.sql"]


def split_sql(sql_text: str) -> list[str]:
    """按分号切 SQL, 先剔除行注释, 防止 INSERT 被前导 -- 误过滤。"""
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    text = "\n".join(lines)
    return [s.strip() for s in text.split(";") if s.strip()]


def init_mysql() -> None:
    print("==> [MySQL] 开始初始化...")
    conn = pymysql.connect(**MYSQL_CONF, charset="utf8mb4", autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS jobhunter "
                        "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci")
            cur.execute("USE jobhunter")
            for script in MYSQL_SCRIPTS:
                sql = (DB_DIR / "mysql" / script).read_text(encoding="utf-8")
                for stmt in split_sql(sql):
                    # 跳过脚本里重复的 USE(上面已选库)
                    if stmt.upper().startswith("USE "):
                        continue
                    cur.execute(stmt)
                print(f"   ✓ executed {script}")
    finally:
        conn.close()
    print("==> [MySQL] 完成\n")


if __name__ == "__main__":
    try:
        init_mysql()
    except Exception as e:
        print(f"[MySQL] 初始化失败: {e}")
    print("全部完成。")
