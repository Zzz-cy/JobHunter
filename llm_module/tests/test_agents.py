"""
Agent协同层测试脚本

测试内容：
1. 意图识别
2. 各Agent独立执行
3. 工作流执行
4. 并行任务执行
5. 结果汇总
"""
import asyncio
import os
import sys

# 确保能导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from agents.agent_coordinator import (
    get_master_agent, get_workflow_engine,
    JobAnalysisAgent, SkillGapAgent, LearningPathAgent,
    TrendPredictionAgent, ReportGenerationAgent,
    AgentTask
)

load_dotenv()


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_intent_recognition():
    """测试意图识别"""
    print_section("测试1: 意图识别")

    master = get_master_agent()

    test_inputs = [
        "Python后端开发需要什么技能？",
        "我会Java，想转数据分析，差什么？",
        "如何从前端转全栈开发？",
        "AI行业未来什么技能最重要？",
        "帮我出一份数据分析行业报告",
        "什么是微服务架构？",
    ]

    for user_input in test_inputs:
        print(f"\n用户: {user_input}")
        intent = await master.recognize_intent(user_input)
        print(f"意图: {intent.get('intent')} (置信度: {intent.get('confidence', 0):.2f})")
        print(f"理由: {intent.get('reasoning', 'N/A')[:100]}...")


async def test_job_analysis_agent():
    """测试岗位分析Agent"""
    print_section("测试2: 岗位分析Agent")

    agent = JobAnalysisAgent()
    task = AgentTask(
        task_type="job_analysis",
        params={"job_title": "Python后端工程师", "industry": "互联网"}
    )

    result = await agent.execute(task)

    if result.success:
        print(f"✓ 分析成功")
        data = result.data
        print(f"  岗位概述: {data.get('job_overview', 'N/A')[:100]}...")
        print(f"  核心技能: {data.get('required_skills', [])[:5]}")
        print(f"  薪资范围: {data.get('salary_range', {})}")
        print(f"  相似岗位: {data.get('similar_jobs', [])[:3]}")
    else:
        print(f"✗ 分析失败: {result.error}")


async def test_skill_gap_agent():
    """测试能力差距分析Agent"""
    print_section("测试3: 能力差距分析Agent")

    agent = SkillGapAgent()
    task = AgentTask(
        task_type="skill_gap",
        params={
            "current_skills": ["Java", "Spring Boot", "MySQL"],
            "target_job": "Python后端工程师"
        }
    )

    result = await agent.execute(task)

    if result.success:
        print(f"✓ 分析成功")
        data = result.data
        print(f"  整体匹配度: {data.get('overall_match_score', 'N/A')}")
        print(f"  缺失技能: {data.get('missing_skills', [])[:5]}")
        print(f"  优势: {data.get('strengths', [])[:3]}")
    else:
        print(f"✗ 分析失败: {result.error}")


async def test_learning_path_agent():
    """测试学习路径规划Agent"""
    print_section("测试4: 学习路径规划Agent")

    agent = LearningPathAgent()
    task = AgentTask(
        task_type="learning_path",
        params={
            "current_skills": ["HTML", "CSS", "JavaScript"],
            "target_skills": ["Python", "Django", "全栈开发"],
            "time_budget": "6个月"
        }
    )

    result = await agent.execute(task)

    if result.success:
        print(f"✓ 规划成功")
        data = result.data
        learning_path = data.get('learning_path', {})
        print(f"  路径概述: {learning_path.get('overview', 'N/A')[:100]}...")
        phases = learning_path.get('phases', [])
        print(f"  学习阶段数: {len(phases)}")
        if phases:
            print(f"  第一阶段: {phases[0].get('phase_name', 'N/A')}")
    else:
        print(f"✗ 规划失败: {result.error}")


async def test_trend_prediction_agent():
    """测试趋势预测Agent"""
    print_section("测试5: 趋势预测Agent")

    agent = TrendPredictionAgent()
    task = AgentTask(
        task_type="trend_prediction",
        params={
            "industry": "人工智能",
            "skill": "Python",
            "timeframe": "未来3年"
        }
    )

    result = await agent.execute(task)

    if result.success:
        print(f"✓ 预测成功")
        data = result.data
        trend = data.get('trend_analysis', {})
        print(f"  行业趋势: {trend.get('industry_overview', 'N/A')[:100]}...")
        print(f"  增长轨迹: {trend.get('growth_trajectory', 'N/A')}")
    else:
        print(f"✗ 预测失败: {result.error}")


async def test_report_generation_agent():
    """测试报告生成Agent"""
    print_section("测试6: 报告生成Agent")

    agent = ReportGenerationAgent()

    # 模拟其他Agent的分析结果
    mock_results = [
        {"agent": "岗位分析Agent", "job_title": "Python后端工程师", "key_skills": ["Python", "Django", "MySQL"]},
        {"agent": "趋势预测Agent", "trend": "Python需求持续增长", "growth": "15%每年"},
    ]

    task = AgentTask(
        task_type="report_generation",
        params={
            "analysis_results": mock_results,
            "report_type": "综合报告"
        }
    )

    result = await agent.execute(task)

    if result.success:
        print(f"✓ 报告生成成功")
        data = result.data
        report = data.get('report', '')
        print(f"  报告长度: {len(report)} 字符")
        print(f"  报告预览:\n{report[:500]}...")
    else:
        print(f"✗ 报告生成失败: {result.error}")


async def test_master_agent():
    """测试Master Agent完整流程"""
    print_section("测试7: Master Agent完整流程")

    master = get_master_agent()

    user_input = "Python后端开发需要什么技能？"
    print(f"用户输入: {user_input}")

    result = await master.process(user_input)

    print(f"\n意图识别: {result.get('intent', {}).get('intent', 'N/A')}")
    print(f"涉及任务: {[t.get('task_type') for t in result.get('tasks', [])]}")
    print(f"最终回答:\n{result.get('answer', 'N/A')[:500]}...")


async def test_workflow_engine():
    """测试工作流引擎"""
    print_section("测试8: 工作流引擎")

    engine = get_workflow_engine()

    # 测试各种工作流
    workflows = [
        ("job_analysis", {"query": "Python后端开发需要什么技能？"}),
        ("trend_analysis", {"query": "AI行业未来什么技能最重要？"}),
    ]

    for workflow_type, params in workflows:
        print(f"\n--- 工作流: {workflow_type} ---")
        result = await engine.execute_workflow(workflow_type, params)
        if "error" in result:
            print(f"✗ 失败: {result['error']}")
        else:
            print(f"✓ 成功")
            print(f"  结果: {str(result.get('answer', 'N/A'))[:200]}...")


async def test_parallel_execution():
    """测试并行执行"""
    print_section("测试9: 并行任务执行")

    master = get_master_agent()

    # 创建多个独立任务
    tasks = [
        AgentTask("job_analysis", {"job_title": "Python后端工程师", "industry": "互联网"}),
        AgentTask("job_analysis", {"job_title": "Java后端工程师", "industry": "互联网"}),
        AgentTask("job_analysis", {"job_title": "前端工程师", "industry": "互联网"}),
    ]

    import time
    start = time.time()
    results = await master.execute_tasks(tasks)
    elapsed = time.time() - start

    print(f"并行执行 {len(tasks)} 个任务，耗时: {elapsed:.2f}秒")
    for task_type, result in results.items():
        status = "✓" if result.success else "✗"
        print(f"  {status} {task_type}")


async def main():
    """主函数"""
    print("=" * 70)
    print("  Agent协同层测试脚本")
    print("  测试内容: 1个Master Agent + 5个专业子Agent + 工作流引擎")
    print("=" * 70)

    # 检查配置
    api_key = os.getenv("LLM_API_KEY") or os.getenv("ZHIPU_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("\n警告: 未配置API Key，测试将使用模拟数据")
        print("请在 .env 文件中设置 LLM_API_KEY 或 ZHIPU_API_KEY")

    # 运行测试
    await test_intent_recognition()
    await test_job_analysis_agent()
    await test_skill_gap_agent()
    await test_learning_path_agent()
    await test_trend_prediction_agent()
    await test_report_generation_agent()
    await test_master_agent()
    await test_workflow_engine()
    await test_parallel_execution()

    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
