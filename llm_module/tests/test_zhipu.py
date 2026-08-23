"""
智谱AI (Zhipu) GLM API测试脚本

使用方法:
    1. 在 .env 文件中配置 ZHIPU_API_KEY
    2. 运行: python test_zhipu.py

测试内容:
    - 基础对话 (chat)
    - 流式对话 (chat_stream)
    - JSON模式 (response_format)
    - 知识抽取 (extract_json)
"""
import asyncio
import os
import sys

# 确保能导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from services.llm_service import get_llm_service, LLMService

load_dotenv()


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_basic_chat():
    """测试基础对话"""
    print_section("测试1: 基础对话 (chat)")

    llm = get_llm_service()

    messages = [
        {"role": "system", "content": "你是一位专业的人力资源助手。"},
        {"role": "user", "content": "请用一句话介绍Python开发工程师这个岗位的核心技能。"},
    ]

    print(f"模型: {llm.model}")
    print(f"API Base: {llm.api_base}")
    print("发送请求...")

    response = await llm.chat(messages)

    print(f"回复: {response[:200]}")
    print("状态: ✓ 成功" if "调用" not in response else f"状态: ✗ 失败 - {response}")


async def test_stream_chat():
    """测试流式对话"""
    print_section("测试2: 流式对话 (chat_stream)")

    llm = get_llm_service()

    messages = [
        {"role": "user", "content": "请列举3个Java开发工程师需要掌握的核心技能。"},
    ]

    print("发送流式请求...")
    print("回复: ", end="", flush=True)

    try:
        async for chunk in llm.chat_stream(messages):
            print(chunk, end="", flush=True)
        print("\n状态: ✓ 成功")
    except Exception as e:
        print(f"\n状态: ✗ 失败 - {str(e)}")


async def test_json_mode():
    """测试JSON模式输出"""
    print_section("测试3: JSON模式 (response_format)")

    llm = get_llm_service()

    messages = [
        {"role": "system", "content": "你是一个数据抽取助手。"},
        {"role": "user", "content": "请抽取以下岗位描述中的技能要求，以JSON格式输出。"
            "岗位描述: 招聘Python后端工程师，要求精通Django、FastAPI框架，熟悉PostgreSQL和Redis，了解Docker和Kubernetes。"},
    ]

    print("发送JSON模式请求...")

    response = await llm.chat(
        messages,
        response_format={"type": "json_object"},
    )

    import json
    try:
        data = json.loads(response)
        print(f"JSON解析成功: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
        print("状态: ✓ 成功")
    except json.JSONDecodeError:
        print(f"JSON解析失败，原始响应: {response[:200]}")
        print("状态: ✗ 失败")


async def test_extract_json():
    """测试知识抽取JSON功能"""
    print_section("测试4: 知识抽取 (extract_json)")

    llm = get_llm_service()

    prompt = """请从以下岗位描述中抽取技能要求：

岗位描述: 招聘高级Java开发工程师，要求精通Spring Boot、Spring Cloud微服务架构，
熟悉MySQL、Redis、Elasticsearch，了解Kafka消息队列，有Docker和Kubernetes部署经验。

请输出JSON格式：
{
    "skills": ["技能1", "技能2", ...],
    "frameworks": ["框架1", "框架2", ...],
    "databases": ["数据库1", "数据库2", ...]
}"""

    result = await llm.extract_json(prompt)

    import json
    print(f"抽取结果: {json.dumps(result, ensure_ascii=False, indent=2)[:400]}")
    print("状态: ✓ 成功" if "error" not in result else f"状态: ✗ 失败")


async def test_different_models():
    """测试不同GLM模型"""
    print_section("测试5: 不同GLM模型")

    models = ["glm-4-flash", "glm-4-air", "glm-4"]

    for model in models:
        print(f"\n--- 测试模型: {model} ---")

        # 创建临时LLM服务实例
        original_model = os.environ.get("LLM_MODEL", "")
        os.environ["LLM_MODEL"] = model

        # 重置单例以使用新配置
        import services.llm_service as llm_module
        llm_module._llm_service = None

        llm = get_llm_service()

        messages = [
            {"role": "user", "content": "你好，请用一句话介绍自己。"},
        ]

        response = await llm.chat(messages)
        print(f"回复: {response[:100]}")
        print(f"状态: {'✓ 成功' if '调用' not in response else '✗ 失败'}")

        # 恢复
        os.environ["LLM_MODEL"] = original_model
        llm_module._llm_service = None


async def test_error_handling():
    """测试错误处理"""
    print_section("测试6: 错误处理")

    # 测试无效API Key
    import services.llm_service as llm_module
    from utils.config import ZHIPU_CONFIG

    # 保存原始配置
    original_key = ZHIPU_CONFIG["api_key"]

    # 模拟无效Key
    ZHIPU_CONFIG["api_key"] = "invalid_key"

    # 重置单例
    llm_module._llm_service = None
    llm = get_llm_service()

    messages = [{"role": "user", "content": "你好"}]
    response = await llm.chat(messages)

    print(f"无效Key响应: {response[:200]}")
    print("状态: ✓ 错误处理正常" if "401" in response or "认证" in response else "状态: ? 未触发预期错误")

    # 恢复配置
    ZHIPU_CONFIG["api_key"] = original_key
    llm_module._llm_service = None


async def main():
    """主函数"""
    print("=" * 60)
    print("  智谱AI (Zhipu) GLM API 测试脚本")
    print("=" * 60)

    # 检查配置
    api_key = os.getenv("ZHIPU_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("\n错误: 未配置API Key")
        print("请在 .env 文件中设置:")
        print("  ZHIPU_API_KEY=your_zhipu_api_key")
        print("或")
        print("  LLM_API_KEY=your_zhipu_api_key")
        return

    print(f"\nAPI Key: {'已设置' if api_key else '未设置'}")
    print(f"API Base: {os.getenv('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4')}")
    print(f"模型: {os.getenv('LLM_MODEL', 'glm-4-flash')}")

    # 运行测试
    await test_basic_chat()
    await test_stream_chat()
    await test_json_mode()
    await test_extract_json()
    await test_different_models()
    await test_error_handling()

    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
