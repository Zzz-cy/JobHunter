"""一键导入爬虫数据到数据库。

用法:
    python -m scripts.import_jobs                  # 导入 db/data/jobs_raw.json
    python -m scripts.import_jobs --file 其他.json   # 导入指定文件
    python -m scripts.import_jobs --reset           # 先清空再导入(会丢收藏/投递!)

内部走 json_to_mysql(按 source+source_id 去重), 默认增量, 重复跑安全。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 保证从 backend/ 目录运行时,app 包能被正确导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal   # noqa: E402
from app.utils.jsonToMysqlUtil import json_to_mysql  # noqa: E402


# 默认数据文件:跟 backend/ 同级的 db/data/jobs_raw.json
DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "db" / "data" / "jobs_raw.json"

# 清空时要 TRUNCATE 的表(只清爬虫业务数据,保留用户/字典/简历/推荐/对话)
RESET_TABLES = ["job_skills", "applications", "jobs", "companies"]


async def run_import(file_path: Path, reset: bool = False) -> int:
    """主流程:可选清空 → 读 json → 调 json_to_mysql 入库。返回职位条数。"""

    # ---------- 1. 校验文件 ----------
    if not file_path.exists():
        print(f"[错误] 找不到数据文件: {file_path}")
        print("       把标准格式 json 放到 backend/db/data/jobs_raw.json,")
        print("       或用 --file 指定路径")
        return 1
    if not file_path.suffix == ".json":
        print(f"[错误] 文件必须是 .json 格式,当前: {file_path.suffix}")
        return 1

    # ---------- 2. 可选:清空 ----------
    if reset:
        print("[重置] 开始清空爬虫数据表...")
        import pymysql
        conn = pymysql.connect(
            host="127.0.0.1", user="root", password="123456",
            database="jobhunter", charset="utf8mb4",
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table in RESET_TABLES:
                    cur.execute(f"TRUNCATE TABLE {table}")
                    print(f"       TRUNCATE {table} 完成")
                cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
        finally:
            conn.close()
        print("[重置] 清空完成")
        print()

    # ---------- 3. 读 json ----------
    print(f"[1/2] 读取数据: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        print("       检查文件是不是标准的单个 JSON(不是 jsonl/多行美化 JSON)")
        return 1

    jobs = data.get("jobs", [])
    if not jobs:
        print("[错误] 文件里没有 jobs 数据")
        return 1
    print(f"      待入库 {len(jobs)} 条职位 (crawl_batch={data.get('crawl_batch')})")
    print()

    # ---------- 4. 调现成的入库工具 ----------
    print("[2/2] 开始入库 (json_to_mysql 已处理去重/公司upsert/技能关联/事务)...")
    try:
        async with AsyncSessionLocal() as db:
            await json_to_mysql(data, db)
    except Exception as e:
        print(f"[错误] 入库失败: {e}")
        return 1

    # 主动关闭连接池,避免程序退出时 aiomysql 报 "Event loop is closed" 告警
    from app.core.database import engine
    await engine.dispose()

    print()
    print("[完成] 导入结束")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把爬虫 JSON 数据导入 JobHunter 数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m scripts.import_jobs                  # 增量导入默认文件
    python -m scripts.import_jobs --file x.json    # 导入指定文件
    python -m scripts.import_jobs --reset          # 先清空再导入(会删收藏/投递)
        """,
    )
    parser.add_argument(
        "--file", "-f",
        default=str(DEFAULT_DATA_FILE),
        help=f"要导入的 JSON 文件路径 (默认: {DEFAULT_DATA_FILE})",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="导入前清空 jobs/job_skills/companies/applications(慎用!会丢收藏/投递)",
    )
    args = parser.parse_args(argv)

    return asyncio.run(run_import(Path(args.file).resolve(), reset=args.reset))


if __name__ == "__main__":
    raise SystemExit(main())
