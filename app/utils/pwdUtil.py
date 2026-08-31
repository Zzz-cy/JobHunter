"""密码哈希工具: 直接用 bcrypt(passlib 和 bcrypt 4.x/5.x 不兼容)。

bcrypt 自动加盐, 同密码两次哈希结果不同, 验证时自动取盐比对。
密码上限 72 字节, 超出截断。这是单向哈希, 不是可逆加密。
"""
import bcrypt


def hash_password(password: str) -> str:
    """明文密码 → bcrypt 哈希串(含盐, 每次结果不同)。"""
    # bcrypt 上限 72 字节, 截断超长密码
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)
