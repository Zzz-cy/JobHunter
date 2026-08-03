"""
安全工具 - 输入净化、SQL注入防护、XSS防护
"""
import re
import html
from typing import Any, Dict, List, Optional


# SQL注入危险模式
SQL_INJECTION_PATTERNS = [
    r"(?i)(\b(union)\b.*\b(select)\b)",           # UNION SELECT
    r"(?i)(\b(drop)\b\s+\b(table|database)\b)",   # DROP TABLE/DATABASE
    r"(?i)(\b(delete)\b\s+\b(from)\b)",           # DELETE FROM
    r"(?i)(\b(insert)\b\s+\b(into)\b)",           # INSERT INTO
    r"(?i)(\b(update)\b\s+\w+\s+\b(set)\b)",     # UPDATE ... SET
    r"(?i)(;\s*(select|drop|delete|insert|update)\b)",  # ; SELECT/DROP/...
    r"(?i)(--\s*$)",                               # SQL注释
    r"(?i)(/\*.*\*/)",                             # 多行注释
    r"('(\s|\s)*;)",                               # '; 注入
    r"(\b(exec|execute)\b\s*\()",                  # EXEC/EXECUTE
    r"(\b(waitfor)\b\s+\b(delay)\b)",             # WAITFOR DELAY (盲注)
    r"(\b(benchmark)\b\s*\()",                     # BENCHMARK (盲注)
    r"(\b(sleep)\b\s*\()",                         # SLEEP (盲注)
]

# XSS危险模式
XSS_INJECTION_PATTERNS = [
    r"(?i)<script[^>]*>.*?</script>",             # <script>标签
    r"(?i)javascript\s*:",                         # javascript:协议
    r"(?i)on\w+\s*=",                              # 事件处理器 onXXX=
    r"(?i)<iframe[^>]*>.*?</iframe>",             # <iframe>标签
    r"(?i)<object[^>]*>.*?</object>",             # <object>标签
    r"(?i)<embed[^>]*>",                           # <embed>标签
    r"(?i)eval\s*\(",                              # eval()
    r"(?i)document\.",                             # document.XXX
    r"(?i)window\.",                               # window.XXX
    r"(?i)<img[^>]+on\w+\s*=",                    # <img onerror=...>
]


class InputSanitizer:
    """输入净化器 - SQL注入和XSS防护"""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 10000) -> str:
        """
        净化字符串输入

        Args:
            value: 输入字符串
            max_length: 最大允许长度

        Returns:
            净化后的字符串

        Raises:
            ValueError: 如果检测到恶意输入
        """
        if not isinstance(value, str):
            value = str(value)

        # 长度限制
        if len(value) > max_length:
            value = value[:max_length]

        # 检测SQL注入
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, value):
                raise ValueError(f"检测到潜在的SQL注入攻击，输入已拒绝")

        # 检测XSS
        for pattern in XSS_INJECTION_PATTERNS:
            if re.search(pattern, value):
                raise ValueError(f"检测到潜在的XSS攻击，输入已拒绝")

        # HTML实体编码（保留基本格式）
        sanitized = html.escape(value, quote=True)

        return sanitized

    @staticmethod
    def sanitize_dict(data: Dict[str, Any], max_length: int = 10000) -> Dict[str, Any]:
        """
        递归净化字典中的所有字符串值

        Args:
            data: 输入字典
            max_length: 最大允许长度

        Returns:
            净化后的字典
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value, max_length)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, max_length)
            elif isinstance(value, list):
                sanitized[key] = InputSanitizer.sanitize_list(value, max_length)
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def sanitize_list(data: List[Any], max_length: int = 10000) -> List[Any]:
        """
        递归净化列表中的所有字符串值

        Args:
            data: 输入列表
            max_length: 最大允许长度

        Returns:
            净化后的列表
        """
        if not isinstance(data, list):
            return data

        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(InputSanitizer.sanitize_string(item, max_length))
            elif isinstance(item, dict):
                sanitized.append(InputSanitizer.sanitize_dict(item, max_length))
            elif isinstance(item, list):
                sanitized.append(InputSanitizer.sanitize_list(item, max_length))
            else:
                sanitized.append(item)
        return sanitized

    @staticmethod
    def is_safe_cypher(query: str) -> bool:
        """
        检查Cypher查询是否安全

        禁止：
        - DETACH DELETE（可能删除整个图）
        - CALL（可能调用危险过程）
        - LOAD CSV（可能读取文件）
        """
        dangerous_patterns = [
            r"(?i)\b(detach)\s+\b(delete)\b",
            r"(?i)\b(call)\b",
            r"(?i)\b(load)\s+\b(csv)\b",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, query):
                return False
        return True

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        净化文件名 - 防止路径遍历

        Args:
            filename: 输入文件名

        Returns:
            净化后的文件名
        """
        # 移除路径分隔符
        filename = filename.replace("/", "").replace("\\", "")
        # 移除 ..
        filename = filename.replace("..", "")
        # 只保留安全字符
        filename = re.sub(r'[^\w\-.]', '_', filename)
        # 限制长度
        return filename[:255]
