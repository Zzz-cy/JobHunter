# -*- coding: utf-8 -*-
"""评测公共工具: 读 .env 配置 + 登录拿 token + 字段比对规则"""
import re
import sys
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
API_BASE = "http://127.0.0.1:8000"

# 本机直连客户端: trust_env=False 禁用系统代理(开 Clash 时 httpx 会把
# 127.0.0.1 请求也代理出去, 导致连不上本地服务/返回非 JSON)
client = httpx.Client(trust_env=False, timeout=180)


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def compare_field(field: str, gt, got) -> bool:
    """单个字段比对(合成/真实两套评测共用同一套规则)。

    age/work_years 放宽 ±1, phone 比后 4 位, 其余精确比对。
    """
    if got is None:
        return False
    if field in ("name", "city", "education"):
        return str(got).strip() == str(gt).strip()
    if field == "gender":
        return int(got) == int(gt)
    if field in ("age", "work_years"):
        return abs(int(got) - int(gt)) <= 1
    if field == "phone":
        g, p = digits(str(gt)), digits(str(got))
        return bool(p) and p[-4:] == g[-4:]
    if field == "email":
        return str(got).strip().lower() == str(gt).strip().lower()
    return False


def load_db_config() -> dict:
    """从 backend/.env 读 MySQL 配置(评测脚本直连库取解析结果)。"""
    cfg = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "", "database": "jobhunter"}
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            mapping = {
                "MYSQL_HOST": "host", "MYSQL_PORT": "port",
                "MYSQL_USER": "user", "MYSQL_PASSWORD": "password",
                "MYSQL_DATABASE": "database",
            }
            if k in mapping:
                cfg[mapping[k]] = v
    cfg["port"] = int(cfg["port"])
    return cfg


def login(account: str, password: str) -> str:
    """登录主后端, 返回 JWT。失败直接退出并提示。"""
    try:
        resp = client.post(f"{API_BASE}/auth/login", json={"account": account, "password": password})
        body = resp.json()
    except Exception as exc:
        print(f"[登录请求异常] {exc}")
        print("请确认主后端(8000)已启动")
        sys.exit(1)
    if body.get("code") != 0 or not body.get("data"):
        print(f"[登录失败] code={body.get('code')} message={body.get('message')}")
        print("请用能登录前端的账号重跑, 例:")
        print(f"  python {sys.argv[0]} --account 你的邮箱 --password 你的密码")
        sys.exit(1)
    return body["data"]["token"]
