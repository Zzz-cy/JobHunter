"""
压力测试脚本 - 使用Locust模拟多用户并发

运行方式:
    cd llm_module
    locust -f locustfile.py --host=http://localhost:5173

访问 http://localhost:8089 查看Locust Web UI
"""
from locust import HttpUser, task, between, events
import json
import random


class ChatUser(HttpUser):
    """模拟聊天用户"""

    # 每个用户操作间隔 2-5秒
    wait_time = between(2, 5)

    # 预定义的测试问题
    test_questions = [
        "Python后端开发需要什么技能？",
        "我会Java，想转数据分析，差什么？",
        "如何从前端转全栈开发？",
        "AI行业未来什么技能最重要？",
        "帮我出一份数据分析行业报告",
        "前端和后端的技能要求有什么不同？",
        "基金经理需要什么资质和技能？",
        "临床医师需要什么技能和资质？",
        "质量工程师需要什么技能？",
        "高中数学教师需要什么技能？",
    ]

    industries = ["it", "finance", "healthcare", "manufacturing", "education"]
    roles = ["job_seeker", "hr", "career_planner", "manager"]

    def on_start(self):
        """用户启动时创建会话"""
        self.session_id = None
        self.industry = random.choice(self.industries)
        self.role = random.choice(self.roles)

    @task(10)
    def chat(self):
        """主要任务：发送聊天消息"""
        question = random.choice(self.test_questions)

        payload = {
            "message": question,
            "session_id": self.session_id,
            "industry": self.industry,
            "role": self.role,
        }

        with self.client.post(
            "/agents/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("session_id"):
                        self.session_id = data["session_id"]
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    def health_check(self):
        """次要任务：健康检查"""
        self.client.get("/health")

    @task(2)
    def get_intents(self):
        """次要任务：获取意图列表"""
        self.client.get("/agents/intents")

    @task(1)
    def get_metrics(self):
        """次要任务：获取监控指标"""
        self.client.get("/api/v1/admin/metrics")


class WorkflowUser(HttpUser):
    """模拟工作流用户 - 执行完整工作流"""

    wait_time = between(5, 10)

    workflow_types = ["job_analysis", "skill_gap", "learning_path", "trend_analysis", "comprehensive_report"]

    @task
    def execute_workflow(self):
        """执行工作流"""
        workflow_type = random.choice(self.workflow_types)

        payload = {
            "query": random.choice(ChatUser.test_questions),
            "industry": random.choice(ChatUser.industries),
        }

        with self.client.post(
            f"/agents/workflow/{workflow_type}",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# 压测事件钩子
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """记录每个请求的详细信息"""
    if exception:
        print(f"❌ 请求失败: {name} - {exception}")
    elif response_time > 10:
        print(f"⚠️ 慢请求: {name} - {response_time:.2f}s")


@events.test_stop.add_listener
def on_test_stop(**kwargs):
    """测试结束时打印摘要"""
    print("\n📊 压力测试完成")
