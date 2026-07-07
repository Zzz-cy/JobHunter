"""密码哈希工具模块 —— 负责明文密码的加密存储与校验"""

from passlib.context import CryptContext

# 使用 bcrypt 算法进行哈希
# deprecated="auto" 表示自动升级旧版哈希格式（如将来更换算法，旧密码仍可验证）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """将明文密码哈希加密

    每次调用结果不同（bcrypt 自动加盐），但都可以通过 verify_password 验证。

    Args:
        password: 用户输入的明文密码

    Returns:
        bcrypt 哈希字符串，存入数据库的 password 字段
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配

    Args:
        plain: 用户登录时输入的明文密码
        hashed: 数据库中存储的哈希值

    Returns:
        True 匹配，False 不匹配
    """
    return pwd_context.verify(plain, hashed)
