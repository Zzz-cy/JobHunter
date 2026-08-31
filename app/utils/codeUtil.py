"""对外编码生成工具"""
import uuid
from datetime import datetime


def generate_code(prefix: str) -> str:
    """通用编码生成: 前缀 + 日期 + 秒数 + 8位随机

    prefix: 单字母前缀, 如 'J'(职位) / 'C'(公司) / 'U'(用户) / 'R'(简历)
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    second_part = f"{now.hour * 3600 + now.minute * 60 + now.second:05d}"
    rand_part = uuid.uuid4().hex[:8]
    return f"{prefix}{date_part}{second_part}{rand_part}"