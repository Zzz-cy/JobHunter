"""密码哈希工具模块 —— 负责明文密码的哈希存储与校验

直接使用 bcrypt 库(不经过 passlib), 因为:
    - passlib 1.7.4 与 bcrypt 4.x/5.x 不兼容(用了已废弃的 __about__ 属性,
      且自检密码超 72 字节会报错)
    - bcrypt 库本身就提供 hashpw / checkpw, 足够用
    - 少一层依赖, 更轻量

bcrypt 知识点:
    - 每次哈希会自动加盐(salt), 所以同一个密码哈希两次结果不同
    - 验证时把盐从哈希串里取出来, 自动比对
    - 密码最长 72 字节(超出会被 bcrypt 拒绝), 这里手动截断兼容

注意: 这里做的是"哈希"(单向不可逆), 不是"加密"(可逆)。
      哈希适合存密码: 即使数据库泄露, 攻击者也无法还原出明文。
"""
import bcrypt


def hash_password(password: str) -> str:
    """将明文密码哈希成 bcrypt 哈希串。

    每次调用结果不同(bcrypt 自动加盐), 但都可以通过 verify_password 验证。

    Args:
        password: 用户输入的明文密码

    Returns:
        bcrypt 哈希字符串(含盐), 存入数据库的 password_hash 字段
    """
    # bcrypt 上限 72 字节, 截断超长密码(防 ValueError)
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。

    Args:
        plain:  用户登录时输入的明文密码
        hashed: 数据库中存储的哈希值

    Returns:
        True 匹配, False 不匹配
    """
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)
