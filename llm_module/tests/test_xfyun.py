"""
讯飞星火API测试脚本
"""
import os
import time
import hmac
import hashlib
import base64
import json
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

XFYUN_APPID = os.getenv("XFYUN_APPID", "")
XFYUN_APIKEY = os.getenv("XFYUN_APIKEY", "")
XFYUN_APISECRET = os.getenv("XFYUN_APISECRET", "")
API_BASE = "https://spark-api-open.xf-yun.com/v1"

print("=" * 60)
print("讯飞星火API配置验证")
print("=" * 60)
print(f"APPID: {XFYUN_APPID}")
print(f"APIKey: {'已设置' if XFYUN_APIKEY else '未设置'}")
print(f"APISecret: {'已设置' if XFYUN_APISECRET else '未设置'}")
print("=" * 60)

if not all([XFYUN_APPID, XFYUN_APIKEY, XFYUN_APISECRET]):
    print("错误：配置不完整")
    exit(1)

# 生成签名
parsed_url = urlparse(API_BASE)
host = parsed_url.netloc
date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
signature_origin = f"host: {host}\ndate: {date}\nPOST /v1/chat/completions HTTP/1.1"

signature_sha = hmac.new(
    XFYUN_APISECRET.encode('utf-8'),
    signature_origin.encode('utf-8'),
    digestmod=hashlib.sha256
).digest()
signature = base64.b64encode(signature_sha).decode('utf-8')

authorization = (
    f'api_key="{XFYUN_APIKEY}", '
    f'algorithm="hmac-sha256", '
    f'headers="host date request-line", '
    f'signature="{signature}"'
)

headers = {
    "Authorization": authorization,
    "Content-Type": "application/json",
    "Date": date,
    "Host": host,
}

# 测试不同模型
import httpx

models = ["generalv3.5", "generalv3", "pro-128k", "4.0Ultra", "spark-v3.5"]

for model in models:
    print(f"\n测试模型: {model}")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 10,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE}/chat/completions",
                headers=headers,
                json=payload,
            )

            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"  成功! 回复: {data['choices'][0]['message']['content'][:50]}")
            else:
                try:
                    error = response.json()
                    print(f"  错误: {json.dumps(error, ensure_ascii=False)}")
                except:
                    print(f"  响应: {response.text[:200]}")
    except Exception as e:
        print(f"  异常: {str(e)}")
