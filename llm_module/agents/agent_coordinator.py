"""
Agent协同层 - 多智能体协同架构

架构设计: 1个Master Agent + 5个专业子Agent
- Master Agent: 意图识别、任务分解、结果汇总
- 子Agent: 岗位分析、差距分析、学习规划、趋势预测、报告生成

技术选型: 基于现有LLMService实现，不引入LangGraph等重依赖
保持轻量、可控、与现有架构无缝集成
"""
import asyncio
import json
import time 
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, AsyncGenerator

from services.llm_service import get_llm_service, LLMService
from utils.logger import get_logger, trace_id_ctx
logger = get_logger("agents.agent_coordinator")


# ==================== 数据模型定义 ====================

class IntentType(str, Enum):
    """八大意图类别"""
    JOB_ANALYSIS = "job_analysis"           # 岗位能力分析
    SKILL_GAP = "skill_gap"                  # 能力差距分析
    LEARNING_PATH = "learning_path"           # 学习路径规划
    TREND_PREDICTION = "trend_prediction"     # 趋势预测分析
    JOB_COMPARE = "job_compare"             # 岗位对比分析
    RESUME_MATCH = "resume_match"             # 简历岗位匹配
    REPORT_GENERATION = "report_generation"   # 报告生成
    GENERAL_QA = "general_qa"                # 通用问答


class AgentTask:
    """Agent任务定义"""
    def __init__(
        self,
        task_type: str,
        params: Dict[str, Any],
        priority: int = 0,
        depends_on: Optional[List[str]] = None
    ):
        self.task_type = task_type
        self.params = params
        self.priority = priority
        self.depends_on = depends_on or []
        self.result: Optional[Any] = None
        self.status = "pending"  # pending, running, completed, failed
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "params": self.params,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class AgentResult:
    """Agent执行结果"""
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


# ==================== 工具注册表 ====================

class ToolRegistry:
    """
    工具注册表 - 声明Agent可用的外部工具
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any],
                 applicable_scenes: List[str], executor: Any = None):
        """注册工具"""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "applicable_scenes": applicable_scenes,
            "executor": executor,
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return list(self._tools.values())

    def get_tools_for_scene(self, scene: str) -> List[Dict[str, Any]]:
        """获取适用于某个场景的工具"""
        return [
            t for t in self._tools.values()
            if scene in t.get("applicable_scenes", [])
        ]


# 全局工具注册表
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表单例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        # 注册内置工具
        _tool_registry.register(
            name="knowledge_search",
            description="从向量知识库中检索相关信息",
            parameters={"query": "检索查询", "top_k": "返回数量"},
            applicable_scenes=["job_analysis", "skill_gap", "general_qa"],
        )
        _tool_registry.register(
            name="graph_query",
            description="从知识图谱中查询实体关系",
            parameters={"entity_name": "实体名称", "depth": "搜索深度"},
            applicable_scenes=["job_analysis", "skill_gap", "learning_path"],
        )
        _tool_registry.register(
            name="skill_database",
            description="从技能数据库中搜索技能信息",
            parameters={"keyword": "搜索关键词", "category": "技能类别"},
            applicable_scenes=["job_analysis", "skill_gap"],
        )
        _tool_registry.register(
            name="job_search",
            description="从主库检索真实在招岗位(含公司/城市/薪资/要求)。用户问岗位机会/薪资/招聘条件/转岗机会时用它",
            parameters={"keyword": "岗位/技能关键词", "city": "城市", "job_type": "工作类型", "limit": "返回条数(默认8)"},
            applicable_scenes=["job_analysis", "job_compare", "skill_gap", "learning_path", "resume_match", "general_qa"],
        )
        _tool_registry.register(
            name="jd_parser",
            description="解析岗位描述文本，提取结构化信息",
            parameters={"content": "JD文本内容"},
            applicable_scenes=["job_analysis", "resume_match"],
        )
        _tool_registry.register(
            name="web_search",
            description="联网搜索最新信息，获取行业动态、薪资数据、招聘趋势等",
            parameters={"query": "搜索关键词", "max_results": "最大结果数(默认5)"},
            applicable_scenes=["job_analysis", "trend_prediction", "general_qa"],
        )
        _tool_registry.register(
            name="calculator",
            description="数值计算工具，用于薪资对比、百分比计算、数据分析等",
            parameters={"expression": "数学表达式(如'15000*1.2')", "description": "计算说明"},
            applicable_scenes=["job_analysis", "job_compare", "skill_gap"],
        )
    return _tool_registry


# ==================== 基础Agent抽象类 ====================

class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.llm = get_llm_service()

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """执行Agent任务"""
        pass

    async def _call_llm(
        self,
        prompt: str,
        system_role: str = "",
        use_json: bool = False,
        task_type: str = "default",
        attempt: int = 0,
    ) -> str:
        """
        调用大模型，支持任务类型路由、重试时模型降级和prompt简化

        Args:
            prompt: 用户提示词
            system_role: 系统角色
            use_json: 是否使用JSON模式
            task_type: 任务类型
            attempt: 当前重试次数（0=首次，>0=重试）
        """
        from core.error_handler import PromptSimplifier, ModelFallback

        # 重试时简化prompt
        if attempt > 0:
            prompt = PromptSimplifier.simplify_prompt(prompt, attempt)

        messages = []
        if system_role:
            # 重试时也简化系统提示词
            if attempt > 0:
                system_role = PromptSimplifier.simplify_prompt(system_role, attempt)
            messages.append({"role": "system", "content": system_role})
        messages.append({"role": "user", "content": prompt})

        # 重试时使用模型降级
        if attempt > 0:
            fallback = ModelFallback(self.llm)
            return await fallback.call_with_fallback(
                messages,
                task_type=task_type,
                response_format={"type": "json_object"} if use_json else None,
                attempt=attempt,
            )

        if use_json:
            return await self.llm.chat(
                messages,
                task_type=task_type,
                response_format={"type": "json_object"}
            )
        return await self.llm.chat(messages, task_type=task_type)


# ==================== 5个专业子Agent ====================

class JobAnalysisAgent(BaseAgent):
    """① 岗位分析Agent - 行业研究员"""
    TASK_TYPE = "job_analysis"

    def __init__(self):
        super().__init__(
            name="岗位分析Agent",
            description="分析特定岗位的技能要求、薪资水平、学历经验要求等"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行岗位分析
        输入: {"job_title": "Python后端工程师", "industry": "互联网"}
        输出: 岗位技能画像、薪资范围、学历经验要求、相似岗位推荐
        """
        params = task.params
        job_title = params.get("job_title", "")
        industry = params.get("industry", "")
        # 可选: 主站"问顾问"入口带来的具体岗位JD(见 MasterAgent._apply_job_context)
        job_jd = params.get("job_jd", "")
        jd_line = f"\n以下为该岗位的真实招聘JD(请以其为主要依据分析，不要只凭常识):\n{job_jd}\n" if job_jd else ""
        # 可选: 主库在招岗位口径数据(见 MasterAgent._inject_platform_facts)
        platform_facts = params.get("platform_facts", "")
        facts_line = (f"\n【平台真实数据】以下为可引用的在招岗位口径数字(岗位数/城市分布等), 也是唯一允许引用的统计数字:\n{platform_facts}\n"
                      f"引用规则(只在引用数据的句子标注, 不要全文刷标):\n"
                      f"1. 只有在引用上方某个具体数字/岗位时, 才在该句句末标注一次[数据来源: 主库在招岗位库];\n"
                      f"2. 同一数字全文中只标注首次出现, 全文标注总计不超过5处;\n"
                      f"3. 未引用上方数字的纯分析/推断/建议句子不得标注;\n"
                      f"4. 上方数据里没有的数字一律不得编造。\n"
                      f"例: 应写『全国在招Python后端岗位仅14个[数据来源: 主库在招岗位库], 需求集中』。\n"
                      if platform_facts else "")

        # 获取行业感知的Prompt上下文
        from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        ctx = INDUSTRY_PROMPT_CONTEXT.get(industry_key, INDUSTRY_PROMPT_CONTEXT.get(DEFAULT_INDUSTRY, {}))

        logger.info(f"[{self.name}] 开始分析岗位: {job_title} (行业: {industry})")

        prompt = f"""你是一位资深的{ctx.get('industry_name', '')}行业人力资源研究员。请对以下岗位进行深度分析，并直接输出纯文本段落（不要输出JSON格式、不要输出列表、不要输出结构化数据、不要使用表格）：

岗位名称: {job_title}
所属行业: {industry}
{jd_line}
{facts_line}
请用自然流畅的中文段落，输出以下内容：

首先是岗位概述，介绍这个岗位的主要职责和工作内容。然后说明从事这个岗位需要掌握哪些核心技能，以及有哪些加分技能可以让你更有竞争力。接着按类别说明需要的技能，包括{ctx.get('skill_categories', '核心专业技能')}等方面。再谈谈这个岗位的薪资水平，用文字描述初级、中级和高级岗位的大致薪资范围。然后说明需要什么学历背景和工作经验。之后列举一些类似或相关的岗位。再描述一下从入门到高级的职业晋升路线。最后分析一下这个岗位的市场前景。

重要提示：
- 必须直接输出纯文本段落
- 不要输出JSON格式
- 不要使用项目符号或编号列表
- 不要使用加粗标记
- 绝对不要使用任何形式的表格（包括Markdown表格、竖线分隔、横线分隔等），所有信息一律用段落文字描述
- 每个部分之间用空行分隔
- 语言要像给求职者写的一份岗位分析报告"""

        try:
            response = await self._call_llm(prompt, use_json=False, task_type=self.TASK_TYPE)

            return AgentResult(
                success=True,
                data={"report": response},
                metadata={"agent": self.name, "job_title": job_title}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


class SkillGapAgent(BaseAgent):
    """② 能力差距分析Agent - 能力评估师"""
    TASK_TYPE = "skill_gap"

    def __init__(self):
        super().__init__(
            name="能力差距分析Agent",
            description="评估用户现有能力与目标岗位的差距，计算匹配度"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行能力差距分析
        输入: {"current_skills": [...], "target_job": "...", "user_profile": {...}}
        输出: 匹配度评分、雷达图数据、关键差距排序、提升优先级建议
        """
        params = task.params
        current_skills = params.get("current_skills", [])
        target_job = params.get("target_job", "")
        industry = params.get("industry", "")
        # 可选: 主库简历画像注入(见 MasterAgent._apply_user_profile)
        user_background = params.get("user_background", "")
        # 可选: 主站"问顾问"入口带来的具体岗位JD(见 MasterAgent._apply_job_context)
        job_jd = params.get("job_jd", "")
        jd_line = f"目标岗位真实JD:\n{job_jd}\n" if job_jd else ""

        # 获取行业感知的Prompt上下文
        from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        ctx = INDUSTRY_PROMPT_CONTEXT.get(industry_key, INDUSTRY_PROMPT_CONTEXT.get(DEFAULT_INDUSTRY, {}))

        logger.info(f"[{self.name}] 分析技能差距: {target_job} (行业: {industry})")

        bg_line = f"用户基础背景(自动读取其主库简历):\n{user_background}\n" if user_background else ""
        prompt = f"""你是一位资深{ctx.get('industry_name', '')}职业规划师。请评估以下用户与目标岗位的能力差距：

用户当前技能: {', '.join(current_skills)}
{bg_line}目标岗位: {target_job}
{jd_line}
请用段落文本（不要用列表或JSON格式）输出以下内容：

整体匹配度评估：用户与目标岗位的整体匹配程度如何，给出一个总体评价。用一段自然的文字描述。

技能对比分析：逐项分析用户现有技能与岗位要求的匹配情况，哪些技能已经具备，哪些还有差距。用段落描述，不要列清单。

优势分析：用户在这个岗位上有哪些优势。用段落描述。

差距分析：用户与岗位要求相比，主要差距在哪里。用段落描述。

提升优先级建议：应该优先提升哪些技能，为什么。用段落描述。

学习建议：针对差距给出具体的学习建议和时间规划。用段落描述。

要求：
- 用自然流畅的段落输出，避免使用项目符号或编号列表
- 语言专业但亲切，像一位资深职业规划师在给求职者做一对一咨询
- 每个部分之间用空行分隔
- 绝对不要使用任何形式的表格（包括Markdown表格、竖线分隔、横线分隔等），所有信息一律用段落文字描述
- 不要加粗标记，保持纯文本风格
- 给出具体、可操作的建议，不要泛泛而谈"""

        try:
            response = await self._call_llm(prompt, use_json=False, task_type=self.TASK_TYPE)

            return AgentResult(
                success=True,
                data={"report": response},
                metadata={"agent": self.name, "target_job": target_job}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


class LearningPathAgent(BaseAgent):
    """③ 学习路径规划Agent - 职业规划师"""
    TASK_TYPE = "learning_path"

    def __init__(self):
        super().__init__(
            name="学习路径规划Agent",
            description="为用户制定技能提升路线，推荐学习资源"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行学习路径规划
        输入: {"current_skills": [...], "target_skills": [...], "time_budget": "3个月"}
        输出: 分阶段学习计划、推荐资源、里程碑检查点
        """
        params = task.params
        current_skills = params.get("current_skills", [])
        target_skills = params.get("target_skills", [])
        time_budget = params.get("time_budget", "3个月")
        industry = params.get("industry", "")
        # 可选: 主库简历画像注入(见 MasterAgent._apply_user_profile)
        user_background = params.get("user_background", "")

        # 获取行业感知的Prompt上下文
        from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        ctx = INDUSTRY_PROMPT_CONTEXT.get(industry_key, INDUSTRY_PROMPT_CONTEXT.get(DEFAULT_INDUSTRY, {}))

        logger.info(f"[{self.name}] 规划学习路径，目标: {target_skills} (行业: {industry})")

        bg_line = f"用户基础背景(自动读取其主库简历):\n{user_background}\n" if user_background else ""
        prompt = f"""你是一位资深{ctx.get('industry_name', '')}职业规划师。请为用户制定详细的学习路径：

用户当前技能: {', '.join(current_skills)}
{bg_line}目标技能: {', '.join(target_skills)}
时间预算: {time_budget}

请用段落文本（不要用列表或JSON格式）输出以下内容：

学习路径概述：整体学习策略和阶段划分。用段落描述。

分阶段学习计划：每个阶段需要学习什么内容，预计多长时间。用段落描述，不要列清单。

技能依赖关系：各项技能之间的依赖关系，应该先学什么后学什么。用段落描述。

推荐学习资源：推荐一些优质的学习资源，如书籍、课程、项目等。用段落描述。

实战项目建议：建议做一些什么样的实战项目来巩固所学。用段落描述。

学习时间安排：如何合理安排学习时间，每天/每周需要投入多少时间。用段落描述。

里程碑检查点：设置哪些检查点来验证学习效果。用段落描述。

学习建议与注意事项：给用户的额外建议和提醒。用段落描述。

要求：
- 用自然流畅的段落输出，避免使用项目符号或编号列表
- 语言亲切实用，像一位经验丰富的导师在给学生做学习规划
- 每个部分之间用空行分隔
- 绝对不要使用任何形式的表格（包括Markdown表格、竖线分隔、横线分隔等），所有信息一律用段落文字描述
- 不要加粗标记，保持纯文本风格
- 给出具体、可执行的建议，不要泛泛而谈"""

        try:
            response = await self._call_llm(prompt, use_json=False, task_type=self.TASK_TYPE)

            return AgentResult(
                success=True,
                data={"report": response},
                metadata={"agent": self.name}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 规划失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


class TrendPredictionAgent(BaseAgent):
    """④ 趋势预测分析Agent - 趋势分析师"""
    TASK_TYPE = "trend_analysis"

    def __init__(self):
        super().__init__(
            name="趋势预测Agent",
            description="分析行业或技能的发展趋势，预测未来热门技能"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行趋势预测分析
        输入: {"industry": "互联网", "skill": "Python", "timeframe": "未来3年"}
        输出: 热门/新兴/衰退技能排行、未来趋势预测、职业发展建议
        """
        params = task.params
        industry = params.get("industry", "")
        skill = params.get("skill", "")
        timeframe = params.get("timeframe", "未来3年")
        # 可选: 主库在招岗位口径数据(见 MasterAgent._inject_platform_facts)
        platform_facts = params.get("platform_facts", "")
        facts_line = (f"\n【平台真实数据】以下为可引用的在招岗位口径数字(岗位数/城市分布等), 也是唯一允许引用的统计数字:\n{platform_facts}\n"
                      f"引用规则(只在引用数据的句子标注, 不要全文刷标):\n"
                      f"1. 只有在引用上方某个具体数字/岗位时, 才在该句句末标注一次[数据来源: 主库在招岗位库];\n"
                      f"2. 同一数字全文中只标注首次出现, 全文标注总计不超过5处;\n"
                      f"3. 未引用上方数字的纯分析/推断/建议句子不得标注;\n"
                      f"4. 上方数据里没有的数字一律不得编造。\n"
                      f"例: 应写『全国在招Python后端岗位仅14个[数据来源: 主库在招岗位库], 需求集中』。\n"
                      if platform_facts else "")

        # 获取行业感知的Prompt上下文
        from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        ctx = INDUSTRY_PROMPT_CONTEXT.get(industry_key, INDUSTRY_PROMPT_CONTEXT.get(DEFAULT_INDUSTRY, {}))

        logger.info(f"[{self.name}] 分析趋势: {industry} - {skill}")

        prompt = f"""你是一位资深{ctx.get('industry_name', '')}行业趋势分析师。请分析以下领域的发展趋势：

行业: {industry}
关注技能: {skill}
预测时间范围: {timeframe}
{facts_line}
请用段落文本（不要用列表或JSON格式）输出以下内容：

行业整体趋势：该行业目前的发展状况和未来走向。用段落描述。

技能需求变化：哪些技能正在兴起，哪些技能保持稳定，哪些技能逐渐衰退。用段落描述。

市场需求预测：未来该领域的人才需求会如何变化。用段落描述。

薪资趋势：该领域薪资水平的变化趋势。用段落描述。

新兴机会：出现了哪些新的职业机会和发展方向。用段落描述。

发展建议：给从业者或求职者的建议。用段落描述。

要求：
- 用自然流畅的段落输出，避免使用项目符号或编号列表
- 语言专业有深度，像一份行业研究报告
- 绝对不要使用任何形式的表格（包括Markdown表格、竖线分隔、横线分隔等），所有信息一律用段落文字描述
- 每个部分之间用空行分隔
- 不要加粗标记，保持纯文本风格"""

        try:
            response = await self._call_llm(prompt, use_json=False, task_type=self.TASK_TYPE)

            return AgentResult(
                success=True,
                data={"report": response},
                metadata={"agent": self.name, "industry": industry, "skill": skill}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


class ReportGenerationAgent(BaseAgent):
    """⑤ 报告生成Agent - 报告撰写人"""
    TASK_TYPE = "report_generation"

    def __init__(self):
        super().__init__(
            name="报告生成Agent",
            description="整合各Agent分析结果，生成结构化综合报告"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行报告生成
        输入: {"analysis_results": [...], "report_type": "综合报告", "format": "markdown"}
        输出: Markdown格式综合报告
        """
        params = task.params
        analysis_results = params.get("analysis_results", [])
        report_type = params.get("report_type", "综合报告")
        # 可选: 主库在招岗位口径数据(见 MasterAgent._inject_platform_facts)
        platform_facts = params.get("platform_facts", "")
        facts_line = (f"\n【平台真实数据】以下为可引用的在招岗位口径数字(岗位数/城市分布等), 也是唯一允许引用的统计数字:\n{platform_facts}\n"
                      f"引用规则(只在引用数据的句子标注, 不要全文刷标):\n"
                      f"1. 只有在引用上方某个具体数字/岗位时, 才在该句句末标注一次[数据来源: 主库在招岗位库];\n"
                      f"2. 同一数字全文中只标注首次出现, 全文标注总计不超过5处;\n"
                      f"3. 未引用上方数字的纯分析/推断/建议句子不得标注;\n"
                      f"4. 上方数据里没有的数字一律不得编造。\n"
                      f"例: 应写『全国在招Python后端岗位仅14个[数据来源: 主库在招岗位库], 需求集中』。\n"
                      if platform_facts else "")

        logger.info(f"[{self.name}] 生成报告: {report_type}")

        # 构建报告上下文
        context = json.dumps(analysis_results, ensure_ascii=False, indent=2)

        prompt = f"""你是一位资深报告撰写专家。请根据以下分析结果生成一份专业的综合报告：

报告类型: {report_type}

分析结果:
{context}

{facts_line}
请生成一份结构化的Markdown格式报告，包含以下内容：
1. 执行摘要（关键发现概述）
2. 详细分析
   - 各维度分析结果
   - 数据支撑和依据
3. 关键发现
   - 最重要的3-5个发现
4. 建议与行动计划
   - 具体可执行的建议
   - 优先级排序
5. 附录
   - 数据来源
   - 分析方法说明

要求：
- 语言专业、简洁
- 数据引用准确
- 建议具体可执行
- 不要使用任何形式的表格，所有信息用段落文字或列表描述"""

        try:
            response = await self._call_llm(prompt)

            return AgentResult(
                success=True,
                data={
                    "report": response,
                    "report_type": report_type,
                    "format": "markdown"
                },
                metadata={"agent": self.name, "report_type": report_type}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 生成失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


class JobCompareAgent(BaseAgent):
    """⑥ 岗位对比Agent - 对比分析师"""
    TASK_TYPE = "job_compare"

    def __init__(self):
        super().__init__(
            name="岗位对比Agent",
            description="对比不同岗位的技能要求、薪资、发展前景等差异"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行岗位对比分析
        输入: {"job_a": "前端开发", "job_b": "后端开发", "industry": "互联网"}
        输出: 两岗位多维度对比分析
        """
        params = task.params
        job_a = params.get("job_a", "")
        job_b = params.get("job_b", "")
        raw_input = params.get("raw_input", "")
        industry = params.get("industry", "")

        # 获取行业感知的Prompt上下文
        from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        ctx = INDUSTRY_PROMPT_CONTEXT.get(industry_key, INDUSTRY_PROMPT_CONTEXT.get(DEFAULT_INDUSTRY, {}))

        logger.info(f"[{self.name}] 对比岗位: {job_a} vs {job_b} (行业: {industry})")

        # 构建岗位信息
        if job_a and job_b:
            job_info = f"岗位A: {job_a}\n岗位B: {job_b}"
        else:
            # 如果未能提取出两个岗位名，让LLM从原始输入中推断
            job_info = f"请从以下用户请求中识别出需要对比的两个岗位：\n{raw_input}"

        prompt = f"""你是一位资深{ctx.get('industry_name', '')}行业人力资源分析师。请对比以下两个岗位的异同：

{job_info}
所属行业: {industry}

请用自然流畅的中文段落（不要用列表或JSON格式）输出以下内容：

核心职责对比：两个岗位的主要工作职责有什么异同。用段落描述。

技能要求对比：两个岗位分别需要哪些{ctx.get('skill_categories', '核心专业技能')}，哪些是共通的，哪些是各自特有的。用段落描述。

薪资水平对比：两个岗位的薪资范围有什么差异。用段落描述。

学历与经验要求对比：两个岗位对学历和工作经验的要求有什么不同。用段落描述。

职业发展路径对比：两个岗位的晋升路线和发展前景有什么差异。用段落描述。

转岗建议：如果要从岗位A转到岗位B（或反之），需要补充哪些能力和知识。用段落描述。

综合评价：对两个岗位做一个总体比较和选择建议。用段落描述。

要求：
- 用自然流畅的段落输出，避免使用项目符号或编号列表
- 对比分析要客观公正，突出差异和共性
- 绝对不要使用任何形式的表格（包括Markdown表格、竖线分隔、横线分隔等），所有对比信息一律用段落文字描述
- 每个部分之间用空行分隔
- 不要加粗标记，保持纯文本风格
- 给出具体、有参考价值的对比分析"""

        try:
            response = await self._call_llm(prompt, use_json=False, task_type=self.TASK_TYPE)

            return AgentResult(
                success=True,
                data={"report": response},
                metadata={"agent": self.name, "job_a": job_a, "job_b": job_b}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 对比失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


class ResumeMatchAgent(BaseAgent):
    """⑦ 简历匹配Agent - 匹配评估师"""
    TASK_TYPE = "resume_match"

    def __init__(self):
        super().__init__(
            name="简历匹配Agent",
            description="评估简历与目标岗位的匹配度，给出优化建议"
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        执行简历岗位匹配评估
        输入: {"resume_content": "...", "target_job": "...", "industry": "..."}
        输出: 匹配度评分、优势/不足分析、简历优化建议
        """
        params = task.params
        resume_content = params.get("resume_content", "")
        target_job = params.get("target_job", "")
        industry = params.get("industry", "")
        # 可选: 主站"问顾问"入口带来的具体岗位JD(见 MasterAgent._apply_job_context)
        job_jd = params.get("job_jd", "")
        jd_line = f"目标岗位真实JD(主库在招):\n{job_jd}\n" if job_jd else ""

        # 获取行业感知的Prompt上下文
        from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        ctx = INDUSTRY_PROMPT_CONTEXT.get(industry_key, INDUSTRY_PROMPT_CONTEXT.get(DEFAULT_INDUSTRY, {}))

        logger.info(f"[{self.name}] 评估简历匹配: 目标={target_job} (行业: {industry})")

        prompt = f"""你是一位资深{ctx.get('industry_name', '')}行业猎头和简历顾问。请评估以下简历与目标岗位的匹配度：

简历内容:
{resume_content}

目标岗位: {target_job}
所属行业: {industry}
{jd_line}
请用自然流畅的中文段落（不要用列表或JSON格式）输出以下内容：

整体匹配度评估：简历与目标岗位的整体匹配程度如何，给出总体评价。用一段自然的文字描述。

匹配优势分析：简历中哪些经历和技能与目标岗位高度匹配。用段落描述。

关键差距分析：简历中缺少哪些目标岗位要求的{ctx.get('skill_categories', '核心专业技能')}和经验。用段落描述。

经历相关性评估：简历中的工作经历与目标岗位的相关程度如何。用段落描述。

简历优化建议：如何优化简历的措辞、结构和内容，使其更贴合目标岗位。用段落描述。

能力补充建议：在求职前应该重点补充哪些能力和经验。用段落描述。

面试准备建议：针对这个岗位，面试时应该如何准备和展示。用段落描述。

要求：
- 用自然流畅的段落输出，避免使用项目符号或编号列表
- 评价要客观中肯，既指出优势也不回避不足
- 每个部分之间用空行分隔
- 绝对不要使用任何形式的表格（包括Markdown表格、竖线分隔、横线分隔等），所有信息一律用段落文字描述
- 不要加粗标记，保持纯文本风格
- 给出具体、可操作的优化建议，不要泛泛而谈"""

        try:
            response = await self._call_llm(prompt, use_json=False, task_type=self.TASK_TYPE)

            return AgentResult(
                success=True,
                data={"report": response},
                metadata={"agent": self.name, "target_job": target_job}
            )
        except Exception as e:
            logger.error(f"[{self.name}] 评估失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name}
            )


# ==================== Master Agent ====================

class ResultCache:
    """中间结果缓存 - LRU + TTL"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}  # key -> {result, timestamp}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, task_type: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        content = f"{task_type}:{json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)}"
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get(self, task_type: str, params: Dict[str, Any]) -> Optional[Any]:
        """获取缓存结果"""
        import time as _time
        key = self._make_key(task_type, params)
        entry = self._cache.get(key)
        if entry and (_time.time() - entry["timestamp"]) < self._ttl:
            return entry["result"]
        if entry:
            del self._cache[key]
        return None

    def set(self, task_type: str, params: Dict[str, Any], result: Any) -> None:
        """缓存结果"""
        import time as _time
        if len(self._cache) >= self._max_size:
            # 淘汰最旧
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
        key = self._make_key(task_type, params)
        self._cache[key] = {"result": result, "timestamp": _time.time()}


class MasterAgent:
    """
    Master Agent - 总调度官

    职责：
    1. 意图识别：判断用户请求属于哪类意图
    2. 任务分解：将请求拆解为有序子任务
    3. 结果汇总：整合各Agent输出，生成最终回答
    """

    # 意图识别提示词（支持多意图和行业感知）
    INTENT_RECOGNITION_PROMPT = """你是一位智能调度系统。请分析用户的请求，判断其意图类别。

用户请求: {user_input}
用户行业上下文: {industry_context}
用户角色: {role_context}

请从以下类别中选择最匹配的一个（或多意图时选两个）：
- job_analysis: 岗位能力分析（如"Python后端需要什么技能？"）
- skill_gap: 能力差距分析（如"我会Java，想转数据分析，差什么？"）
- learning_path: 学习路径规划（如"如何从前端转全栈？"）
- trend_prediction: 趋势预测分析（如"AI行业未来什么技能最重要？"）
- job_compare: 岗位对比分析（如"前端和后端的技能要求有什么不同？"）
- resume_match: 简历岗位匹配（如"我的简历适合投哪些岗位？"）
- report_generation: 报告生成（如"帮我出一份数据分析行业报告"）
- general_qa: 通用问答（其他一般性问题）

请以JSON格式输出：
{{
    "intent": "主意图类别",
    "secondary_intent": "次要意图类别（如无则为null）",
    "confidence": 0.95,
    "extracted_entities": {{
        "job_title": "提取的岗位名称",
        "skills": ["提取的技能"],
        "industry": "提取的行业"
    }},
    "reasoning": "判断理由"
}}"""

    def __init__(self):
        self.name = "Master Agent"
        self.llm = get_llm_service()

        # 并发控制信号量
        from utils.config import RATE_LIMIT_CONFIG
        self._semaphore = asyncio.Semaphore(
            RATE_LIMIT_CONFIG.get("max_concurrent_agents", 5)
        )

        # 结果缓存
        self._result_cache = ResultCache(max_size=100, ttl_seconds=3600)

        # 注册所有子Agent
        self.agents: Dict[str, BaseAgent] = {
            "job_analysis": JobAnalysisAgent(),
            "skill_gap": SkillGapAgent(),
            "learning_path": LearningPathAgent(),
            "trend_prediction": TrendPredictionAgent(),
            "report_generation": ReportGenerationAgent(),
            "job_compare": JobCompareAgent(),
            "resume_match": ResumeMatchAgent(),
        }

        # 意图到Agent的映射
        self.intent_agent_map = {
            IntentType.JOB_ANALYSIS: "job_analysis",
            IntentType.SKILL_GAP: "skill_gap",
            IntentType.LEARNING_PATH: "learning_path",
            IntentType.TREND_PREDICTION: "trend_prediction",
            IntentType.JOB_COMPARE: "job_compare",
            IntentType.RESUME_MATCH: "resume_match",
            IntentType.REPORT_GENERATION: "report_generation",
        }

    async def recognize_intent(
        self,
        user_input: str,
        industry: str = "",
        role: str = "",
    ) -> Dict[str, Any]:
        """
        识别用户意图 - 带行业/角色上下文

        Returns:
            {
                "intent": "意图类别",
                "secondary_intent": "次要意图（可null）",
                "confidence": 0.95,
                "extracted_entities": {...},
                "reasoning": "判断理由"
            }
        """
        logger.info(f"[{self.name}] 识别意图: {user_input[:50]}...")

        prompt = self.INTENT_RECOGNITION_PROMPT.format(
            user_input=user_input,
            industry_context=industry or "未指定",
            role_context=role or "未指定",
        )

        try:
            response = await self.llm.chat(
                [{"role": "user", "content": prompt}],
                task_type="intent_classification",
                response_format={"type": "json_object"}
            )
            result = json.loads(response) if isinstance(response, str) else response

            # 意图校验：确保intent是合法的枚举值
            valid_intents = {i.value for i in IntentType}
            if result.get("intent") not in valid_intents:
                logger.warning(f"非法意图 [{result.get('intent')}]，降级为general_qa")
                result["intent"] = "general_qa"
                result["confidence"] = 0.3

            # 校验次要意图
            secondary = result.get("secondary_intent")
            if secondary and secondary not in valid_intents:
                result["secondary_intent"] = None

            # 置信度校验
            confidence = result.get("confidence", 0)
            result["confidence"] = max(0.0, min(1.0, float(confidence)))

            logger.info(f"[{self.name}] 意图识别结果: {result.get('intent', 'unknown')} (置信度: {result.get('confidence', 0)})")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] 意图识别失败: {str(e)}")
            return {
                "intent": "general_qa",
                "secondary_intent": None,
                "confidence": 0.5,
                "extracted_entities": {},
                "reasoning": f"意图识别失败，降级处理: {str(e)}"
            }

    async def _dynamic_decompose(self, user_input: str, intent_result: Dict[str, Any],
                                 industry: str = "") -> List[AgentTask]:
        """
        LLM动态任务分解 — 根据查询复杂度决定子任务数量和依赖关系

        适用于：复杂查询、多意图、report_generation等需要灵活编排的场景
        """
        entities = intent_result.get("extracted_entities", {})
        intent_str = intent_result.get("intent", "general_qa")

        prompt = f"""你是一个任务规划引擎。根据用户查询，将其分解为有序的子任务。

用户查询: {user_input}
识别意图: {intent_str}
提取实体: {json.dumps(entities, ensure_ascii=False)}
行业上下文: {industry or "未指定"}

可用Agent类型：
- job_analysis: 岗位能力分析
- skill_gap: 能力差距分析
- learning_path: 学习路径规划
- trend_prediction: 趋势预测分析
- job_compare: 岗位对比分析
- resume_match: 简历岗位匹配
- report_generation: 综合报告生成

请以JSON格式输出任务列表：
{{
    "tasks": [
        {{
            "task_type": "agent类型",
            "params": {{"key": "value"}},
            "priority": 0,
            "depends_on": []
        }}
    ]
}}

规则：
1. 优先级0=最高，先执行；数字越大越后执行
2. depends_on列出依赖的task_type（该任务必须先完成）
3. 无依赖的任务可并行执行
4. 参数根据agent类型填写：
   - job_analysis: job_title, industry
   - skill_gap: current_skills(list), target_job, industry
   - learning_path: current_skills(list), target_skills(list), time_budget, industry
   - trend_prediction: industry, skill, timeframe
   - job_compare: job_a, job_b, industry
   - resume_match: resume_content, target_job, industry
   - report_generation: analysis_results, report_type
5. report_generation依赖前面的分析任务
6. 只输出JSON，不要其他内容"""

        try:
            result = await self.llm.extract_json(prompt, task_type="intent_classification")
            tasks_data = result.get("tasks", [])
            tasks = []
            for t in tasks_data:
                task = AgentTask(
                    task_type=t.get("task_type", "general_qa"),
                    params=t.get("params", {}),
                    priority=t.get("priority", 0),
                    depends_on=t.get("depends_on", []),
                )
                tasks.append(task)
            return tasks
        except Exception as e:
            logger.warning(f"动态任务分解失败，回退到硬编码: {e}")
            return []

    async def decompose_task(self, intent_result: Dict[str, Any], user_input: str, industry: str = "") -> List[AgentTask]:
        """
        根据意图分解任务

        Args:
            intent_result: 意图识别结果
            user_input: 用户输入
            industry: 行业上下文

        Returns:
            任务列表
        """
        intent_str = intent_result.get("intent", "general_qa")
        entities = intent_result.get("extracted_entities", {})

        tasks = []

        if intent_str == "job_analysis":
            tasks.append(AgentTask(
                task_type="job_analysis",
                params={
                    "job_title": entities.get("job_title", user_input),
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "skill_gap":
            tasks.append(AgentTask(
                task_type="skill_gap",
                params={
                    "current_skills": entities.get("skills", []),
                    "target_job": entities.get("job_title", ""),
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "learning_path":
            tasks.append(AgentTask(
                task_type="learning_path",
                params={
                    "current_skills": entities.get("skills", []),
                    "target_skills": [entities.get("job_title", "")],
                    "time_budget": "3个月",
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "trend_prediction":
            tasks.append(AgentTask(
                task_type="trend_prediction",
                params={
                    "industry": entities.get("industry", industry),
                    "skill": entities.get("job_title", ""),
                    "timeframe": "未来3年",
                }
            ))

        elif intent_str == "job_compare":
            # 岗位对比：尝试从用户输入中提取两个岗位
            # 如果实体中有两个岗位名则直接使用，否则让Agent从原始输入中推断
            skills_list = entities.get("skills", [])
            job_title = entities.get("job_title", "")
            # 尝试将job_title和skills作为两个对比岗位
            job_a = job_title if job_title else ""
            job_b = skills_list[0] if skills_list else ""
            tasks.append(AgentTask(
                task_type="job_compare",
                params={
                    "job_a": job_a,
                    "job_b": job_b,
                    "raw_input": user_input,
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "resume_match":
            # 简历匹配：从实体中提取简历内容和目标岗位
            tasks.append(AgentTask(
                task_type="resume_match",
                params={
                    "resume_content": user_input,
                    "target_job": entities.get("job_title", ""),
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "report_generation":
            # 报告生成：尝试LLM动态分解，失败则回退到硬编码
            dynamic_tasks = await self._dynamic_decompose(user_input, intent_result, industry)
            if dynamic_tasks:
                tasks.extend(dynamic_tasks)
            else:
                # 回退：硬编码的3步流水线
                tasks.append(AgentTask(
                    task_type="job_analysis",
                    params={"job_title": entities.get("job_title", ""), "industry": entities.get("industry", industry)},
                    priority=0
                ))
                tasks.append(AgentTask(
                    task_type="trend_prediction",
                    params={"industry": entities.get("industry", industry), "skill": entities.get("job_title", "")},
                    priority=0
                ))
                tasks.append(AgentTask(
                    task_type="report_generation",
                    params={"report_type": "综合报告"},
                    priority=1,
                    depends_on=["job_analysis", "trend_prediction"]
                ))

        else:
            # 通用问答，直接回答
            tasks.append(AgentTask(
                task_type="general_qa",
                params={"question": user_input}
            ))

        # 处理次要意图（多意图）
        secondary_intent = intent_result.get("secondary_intent")
        if secondary_intent and secondary_intent != intent_str:
            secondary_tasks = self._decompose_single_intent(
                secondary_intent, entities, user_input, industry
            )
            # 避免重复任务
            existing_types = {t.task_type for t in tasks}
            for st in secondary_tasks:
                if st.task_type not in existing_types:
                    tasks.append(st)

        return tasks

    def _decompose_single_intent(
        self,
        intent_str: str,
        entities: Dict[str, Any],
        user_input: str,
        industry: str = "",
    ) -> List[AgentTask]:
        """分解单个意图为任务列表"""
        tasks = []

        if intent_str == "job_analysis":
            tasks.append(AgentTask(
                task_type="job_analysis",
                params={
                    "job_title": entities.get("job_title", user_input),
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "skill_gap":
            tasks.append(AgentTask(
                task_type="skill_gap",
                params={
                    "current_skills": entities.get("skills", []),
                    "target_job": entities.get("job_title", ""),
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "learning_path":
            tasks.append(AgentTask(
                task_type="learning_path",
                params={
                    "current_skills": entities.get("skills", []),
                    "target_skills": [entities.get("job_title", "")],
                    "time_budget": "3个月",
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "trend_prediction":
            tasks.append(AgentTask(
                task_type="trend_prediction",
                params={
                    "industry": entities.get("industry", industry),
                    "skill": entities.get("job_title", ""),
                    "timeframe": "未来3年",
                }
            ))

        elif intent_str == "job_compare":
            skills_list = entities.get("skills", [])
            job_title = entities.get("job_title", "")
            job_a = job_title if job_title else ""
            job_b = skills_list[0] if skills_list else ""
            tasks.append(AgentTask(
                task_type="job_compare",
                params={
                    "job_a": job_a,
                    "job_b": job_b,
                    "industry": entities.get("industry", industry),
                }
            ))

        elif intent_str == "resume_match":
            tasks.append(AgentTask(
                task_type="resume_match",
                params={
                    "resume_content": "",
                    "target_job": entities.get("job_title", ""),
                    "industry": entities.get("industry", industry),
                }
            ))

        return tasks

    async def execute_tasks(self, tasks: List[AgentTask]) -> Dict[str, AgentResult]:
        """
        执行任务列表
        支持：并行执行无依赖任务、优先级排序、DAG依赖
        """
        results = {}

        # 按优先级排序（priority小的先执行）
        tasks_sorted = sorted(tasks, key=lambda t: t.priority)

        # 分离有依赖和无依赖的任务
        independent_tasks = [t for t in tasks_sorted if not t.depends_on]
        dependent_tasks = [t for t in tasks_sorted if t.depends_on]

        # 并行执行无依赖任务
        if independent_tasks:
            logger.info(f"[{self.name}] 并行执行 {len(independent_tasks)} 个无依赖任务")
            for t in independent_tasks:
                logger.debug(f"执行任务: {t.task_type}, priority={t.priority}, depends_on={t.depends_on}")

            async def _run_with_semaphore(task):
                async with self._semaphore:
                    return await self._execute_single_task(task)

            independent_results = await asyncio.gather(
                *[_run_with_semaphore(task) for task in independent_tasks],
                return_exceptions=True
            )
            for task, result in zip(independent_tasks, independent_results):
                if isinstance(result, Exception):
                    results[task.task_type] = AgentResult(success=False, error=str(result))
                else:
                    results[task.task_type] = result

        # 串行执行有依赖任务
        for task in dependent_tasks:
            # 检查依赖是否完成
            dependencies_met = all(
                dep in results and results[dep].success
                for dep in task.depends_on
            )
            if dependencies_met:
                result = await self._execute_single_task(task)
                results[task.task_type] = result
            else:
                results[task.task_type] = AgentResult(
                    success=False,
                    error=f"依赖任务未完成: {task.depends_on}"
                )

        return results

    async def _select_and_execute_tools(self, task: AgentTask) -> Optional[Dict[str, Any]]:
        """
        工具选择与执行 - 根据任务类型让LLM决定调用哪些工具

        Returns:
            工具结果字典，或None（无适用工具/执行失败）
        """
        from services.tool_executor import get_tool_executor

        registry = get_tool_registry()
        applicable_tools = registry.get_tools_for_scene(task.task_type)

        if not applicable_tools:
            return None

        # 构建工具选择prompt
        tool_descriptions = json.dumps([
            {"name": t.get("name", ""), "description": t.get("description", ""),
             "parameters": t.get("parameters", {})}
            for t in applicable_tools
        ], ensure_ascii=False)

        prompt = f"""基于以下任务，决定是否需要调用工具以及调用哪些工具。

任务类型: {task.task_type}
任务参数: {json.dumps(task.params, ensure_ascii=False, default=str)[:500]}

可用工具:
{tool_descriptions}

请以JSON格式回复:
{{"tool_calls": [{{"tool_name": "工具名", "params": {{参数}}}}]}}
如果不需要工具，回复: {{"tool_calls": []}}"""
        try:
            result = await asyncio.wait_for(
                self.llm.extract_json(
                    prompt,
                    task_type="intent_classification",
                ),
                timeout=15  # 工具选择最多15秒
            )
            tool_calls = result.get("tool_calls", [])

            if not tool_calls:
                return None

            executor = get_tool_executor()
            tool_results = {}
            for tc in tool_calls:
                tool_name = tc.get("tool_name", "")
                tool_params = tc.get("params", {})
                exec_result = await executor.execute(tool_name, tool_params)
                tool_results[tool_name] = exec_result
                logger.info(f"工具执行 [{tool_name}]: success={exec_result['success']}")

            return tool_results
        except Exception as e:
            logger.warning(f"工具选择/执行失败: {e}")
            return None

    async def _execute_single_task(self, task: AgentTask) -> AgentResult:
        """执行单个任务 - 带超时、重试、熔断、全链路追踪"""
        from core.error_handler import (
            retry_with_backoff, get_circuit_breaker,
            AgentTimeout, FallbackHandler, is_retryable_error,
        )
        from utils.config import RATE_LIMIT_CONFIG
        from services.trace_service import get_trace_service

        task.status = "running"
        task.started_at = datetime.now().isoformat()
        start_ts = time.time()

        # 检查结果缓存
        cached = self._result_cache.get(task.task_type, task.params)
        if cached is not None:
            logger.info(f"命中结果缓存 [{task.task_type}]")
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            return AgentResult(success=True, data=cached)

        # 工具选择与执行：在agent执行前，根据任务类型选择并执行工具
        tool_context = None
        try:
            tool_context = await self._select_and_execute_tools(task)
        except Exception as e:
            logger.warning(f"工具选择/执行失败: {e}")

        # 如果有工具结果，注入到任务参数中
        if tool_context:
            task.params["tool_results"] = tool_context

        agent_name = self.intent_agent_map.get(
            IntentType(task.task_type) if task.task_type in [i.value for i in IntentType] else IntentType.GENERAL_QA,
            None
        )

        # 获取指标采集器和追踪服务
        from services.metrics_service import get_metrics_collector
        metrics = get_metrics_collector()
        trace_svc = get_trace_service()

        # 为当前任务创建span
        current_trace_id = trace_id_ctx.get("-")
        span = None
        if current_trace_id != "-":
            span = trace_svc.start_span(
                current_trace_id,
                f"agent_{task.task_type}",
                metadata={"agent": agent_name or task.task_type, "params": str(task.params)[:200]}
            )

        try:
            if agent_name and agent_name in self.agents:
                agent = self.agents[agent_name]

                # 检查熔断器
                cb = get_circuit_breaker(agent_name)
                if not cb.is_available():
                    logger.warning(f"熔断器打开 [{agent_name}]，降级为通用问答")
                    fallback = FallbackHandler(self.llm)
                    fallback_answer = await fallback.fallback_to_general_qa(
                        task.params.get("question", str(task.params)),
                        f"Agent {agent_name} 熔断"
                    )
                    task.status = "completed"
                    task.result = {"answer": fallback_answer}
                    task.completed_at = datetime.now().isoformat()
                    if span:
                        trace_svc.end_span(span, status="completed", error_message="circuit_breaker_open")
                    return AgentResult(success=True, data={"answer": fallback_answer})

                # 带重试和超时的执行
                async def _do_execute():
                    # 单次Agent生成上限90s: 简历匹配/报告等大上下文长输出单次可能30-80s,
                    # 原30s过紧会把"慢但会成功"的生成杀掉再重试, 反把整轮拖到总超时。
                    return await AgentTimeout.execute_with_timeout(
                        agent.execute(task),
                        timeout=90.0,
                        task_type=task.task_type,
                    )

                try:
                    result = await retry_with_backoff(
                        _do_execute,
                        max_retries=2,
                        base_delay=1.0,
                        task_type=task.task_type,
                    )
                    cb.record_success()

                    # Schema校验：校验Agent输出是否符合预定义格式
                    if result.success and result.data:
                        from models.schemas import validate_agent_output
                        validation = validate_agent_output(task.task_type, result.data)
                        if not validation["valid"]:
                            logger.warning(
                                f"Agent输出Schema校验失败 [{task.task_type}]: "
                                f"{validation['errors']}"
                            )
                            # 校验失败但数据存在，降低置信度而非丢弃
                            if isinstance(result.data, dict):
                                result.data["_validation_errors"] = validation["errors"]
                                result.data["_validation_confidence"] = validation["confidence"]
                        elif validation.get("confidence", 1.0) < 0.7:
                            logger.info(
                                f"Agent输出Schema校验通过但置信度低 [{task.task_type}]: "
                                f"confidence={validation['confidence']}"
                            )
                        # 使用校验修正后的数据
                        if validation.get("data") and validation["valid"]:
                            result.data = validation["data"]

                    task.status = "completed" if result.success else "failed"
                    task.result = result.data
                    task.completed_at = datetime.now().isoformat()

                    # 缓存成功结果
                    if result.success and result.data:
                        self._result_cache.set(task.task_type, task.params, result.data)
                    # 记录Agent级指标
                    elapsed = time.time() - start_ts
                    metrics.record_agent_call(agent_name or task.task_type, result.success, elapsed)
                    # 结束span
                    if span:
                        trace_svc.end_span(span, status="completed" if result.success else "failed")
                    return result
                except Exception as e:
                    cb.record_failure()
                    # 重试耗尽，降级为通用问答
                    logger.warning(f"Agent执行失败，降级 [{agent_name}]: {str(e)[:100]}")
                    fallback = FallbackHandler(self.llm)
                    fallback_answer = await fallback.fallback_to_general_qa(
                        str(task.params),
                        str(e)
                    )
                    task.status = "completed"
                    task.result = {"answer": fallback_answer}
                    task.completed_at = datetime.now().isoformat()
                    # 记录降级指标
                    elapsed = time.time() - start_ts
                    metrics.record_agent_call(agent_name or task.task_type, False, elapsed, retry_count=1)
                    # 结束span（降级视为completed）
                    if span:
                        trace_svc.end_span(span, status="completed", error_message=f"降级: {str(e)[:100]}")
                    return AgentResult(success=True, data={"answer": fallback_answer})
            else:
                # 通用问答
                response = await self.llm.chat([
                    {"role": "user", "content": task.params.get("question", "")}
                ])
                task.status = "completed"
                task.result = {"answer": response}
                task.completed_at = datetime.now().isoformat()
                if span:
                    trace_svc.end_span(span, status="completed")
                return AgentResult(success=True, data={"answer": response})
        except Exception as e:
            task.status = "failed"
            task.completed_at = datetime.now().isoformat()
            logger.error(f"任务执行异常: {task.task_type} - {str(e)}")
            if span:
                trace_svc.end_span(span, status="failed", error_message=str(e)[:200])
            return AgentResult(success=False, error=str(e))

    async def summarize_results(self, intent: str, results: Dict[str, AgentResult], user_input: str) -> Dict[str, Any]:
        """
        汇总各Agent结果，生成最终回答

        支持部分结果返回：多任务执行时，部分失败返回成功部分+失败说明
        """
        logger.info(f"[{self.name}] 汇总结果")

        # 分类成功和失败的结果
        success_results = {}
        failed_results = {}
        for k, v in results.items():
            if not v.success:
                failed_results[k] = v.error or "执行失败"
                continue

            # 基本校验：检查数据不为空/None
            if v.data is None:
                logger.warning(f"结果校验失败 [{k}]: data is None")
                failed_results[k] = "结果为空"
                continue

            if isinstance(v.data, dict) and not v.data:
                logger.warning(f"结果校验失败 [{k}]: data is empty dict")
                failed_results[k] = "结果为空字典"
                continue

            if isinstance(v.data, str) and len(v.data.strip()) < 10:
                logger.warning(f"结果校验失败 [{k}]: data too short ({len(v.data)} chars)")
                failed_results[k] = "结果过短"
                continue

            # 简单置信度启发式评估
            confidence = 1.0
            if isinstance(v.data, dict):
                report = v.data.get("report", "")
                if len(report) < 50:
                    confidence = 0.3  # 过短报告 = 低置信度
                elif len(report) < 200:
                    confidence = 0.6
                # 检查幻觉标记
                hallucination_markers = ["我不确定", "这可能不准确", "据我所知没有"]
                if any(marker in report for marker in hallucination_markers):
                    confidence *= 0.7

            v.metadata["confidence"] = confidence
            success_results[k] = v.data

        # 部分结果返回：如果有成功结果也有失败结果，返回成功部分+失败说明
        if success_results and failed_results:
            logger.info(
                f"[{self.name}] 部分结果返回: "
                f"成功={list(success_results.keys())}, "
                f"失败={list(failed_results.keys())}"
            )

        # 构建失败说明
        failure_summary = ""
        if failed_results:
            failure_parts = [f"- {k}: {v}" for k, v in failed_results.items()]
            failure_summary = "\n\n**部分分析未能完成：**\n" + "\n".join(failure_parts)

        if not success_results:
            return {
                "answer": "抱歉，分析过程中出现错误或结果质量不足，请稍后重试。",
                "details": failed_results,
                "partial": False,
            }

        # 如果是单一任务，直接返回结果
        if len(success_results) == 1:
            data = success_results[list(success_results.keys())[0]]
            if isinstance(data, dict):
                answer_text = data.get("report") or data.get("answer") or json.dumps(data, ensure_ascii=False)
            else:
                answer_text = str(data)
            return {
                "answer": answer_text + failure_summary,
                "details": success_results,
                "partial": bool(failed_results),
                "failed_tasks": list(failed_results.keys()) if failed_results else [],
            }

        # 多任务结果汇总
        summary_prompt = f"""请根据以下分析结果，为用户生成一份清晰、结构化的综合回答：

用户请求: {user_input}

分析结果:
{json.dumps(success_results, ensure_ascii=False, indent=2)}

要求：
1. 用中文回答，语言专业、简洁
2. 分点列出关键发现
3. 给出具体、可操作的建议
4. 不要使用任何形式的表格，所有信息用段落文字或列表描述"""

        try:
            summary = await self.llm.chat([{"role": "user", "content": summary_prompt}])
            return {
                "answer": summary + failure_summary,
                "details": success_results,
                "partial": bool(failed_results),
                "failed_tasks": list(failed_results.keys()) if failed_results else [],
            }
        except Exception as e:
            logger.error(f"[{self.name}] 汇总失败: {str(e)}")
            return {
                "answer": "分析完成，但汇总过程中出现错误。" + failure_summary,
                "details": success_results,
                "partial": bool(failed_results),
                "failed_tasks": list(failed_results.keys()) if failed_results else [],
            }

    @staticmethod
    def _format_user_profile(profile: Optional[Dict[str, Any]]) -> str:
        """把主库简历画像压缩成一段中文背景文本, 供 Agent 提示词引用。"""
        if not profile:
            return ""
        lines = []
        meta = []
        if profile.get("name"):
            meta.append(profile["name"])
        if profile.get("city"):
            meta.append(f"坐标{profile['city']}")
        if profile.get("education"):
            meta.append(f"{profile['education']}学历")
        if profile.get("work_years") is not None:
            meta.append(f"{profile['work_years']}年经验")
        if meta:
            lines.append("基本信息: " + "、".join(str(m) for m in meta))
        expect = []
        if profile.get("expect_job"):
            expect.append(profile["expect_job"])
        if profile.get("expect_city"):
            expect.append(profile["expect_city"])
        if expect:
            lines.append("求职意向: " + "、".join(str(e) for e in expect))
        skills = profile.get("skills") or []
        if skills:
            parts = []
            for s in skills:
                nm = s.get("name")
                yrs = s.get("years")
                if nm and yrs is not None:
                    parts.append(f"{nm}(约{yrs}年)")
                elif nm:
                    parts.append(nm)
            if parts:
                lines.append("技能清单: " + "、".join(parts))
        exps = profile.get("experiences") or []
        if exps:
            exp_parts = []
            for e in exps[:6]:
                cn = e.get("company_name")
                ti = e.get("title")
                cur = e.get("is_current")
                sd = str(e.get("start_date") or "")[:7]
                ed = "至今" if cur else str(e.get("end_date") or "")[:7]
                span = f"{sd}-{ed}" if sd else ""
                seg = cn or ""
                if ti:
                    seg = f"{seg}·{ti}" if seg else ti
                if span:
                    seg = f"{seg}({span})" if seg else span
                if seg:
                    exp_parts.append(seg)
            if exp_parts:
                lines.append("经历: " + "; ".join(exp_parts))
        return "\n".join(lines) if lines else ""

    def _apply_user_profile(self, tasks: List[AgentTask],
                            profile: Optional[Dict[str, Any]]) -> None:
        """把已登录用户的真实简历画像注入「关于我」类任务, 让顾问按真实简历作答。

        - resume_match: 用主库真实简历替换「用户原话当简历」的旧逻辑;
        - skill_gap / learning_path: 用户明说技能与简历技能取并集, 并附上背景。
        无画像(未登录/没解析好简历)时静默跳过, 保留原降级逻辑。
        """
        if not profile:
            return
        text = self._format_user_profile(profile)
        prof_skills = [s.get("name") for s in (profile.get("skills") or []) if s.get("name")]
        for t in tasks:
            p = t.params
            if t.task_type == "resume_match":
                if text:
                    p["resume_content"] = text
                if not p.get("target_job") and profile.get("expect_job"):
                    p["target_job"] = profile["expect_job"]
            elif t.task_type in ("skill_gap", "learning_path"):
                existing = [str(s) for s in (p.get("current_skills") or []) if s]
                merged = list(dict.fromkeys(existing + [str(s) for s in prof_skills]))
                if merged:
                    p["current_skills"] = merged
                if text:
                    p["user_background"] = text

    # ==================== 真实岗位结构化推荐(可点卡片) ====================

    @staticmethod
    def _dedup_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按 job_id 去重(多关键词并集检索时可能撞同一岗位)"""
        seen: Dict[int, Dict[str, Any]] = {}
        for j in jobs:
            jid = j.get("job_id")
            if jid is None:
                continue
            if jid not in seen:
                seen[jid] = j
        return list(seen.values())

    async def _build_recommended_jobs(self, tasks: List[AgentTask],
                                      profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """确定性预取真实在招岗位, 附「简历-岗位」匹配分, 供前端渲染可点击职位卡片。

        不依赖 Agent 是否自行决定调 job_search —— 命中求职机会类场景就取主库真数据。
        关键词来源: 任务目标岗位 > 简历求职意向 > 简历技能(多词并集去重, 提高召回);
        有简历文本时调一次 LLM 挑 Top-N 并给分/理由, 失败降级为不带分的真实岗位。
        返回: [{job_id,title,company,city,salary,experience,education,match_score,match_reason}]
        任何异常都静默降级为空数组, 绝不阻塞主回答。
        """
        from services.tool_executor import get_tool_executor

        # 1. 只对求职机会类场景做
        target_scenes = ("resume_match", "skill_gap", "learning_path")
        if not any(t.task_type in target_scenes for t in tasks):
            return []
        try:
            # 2. 确定检索词与城市
            target = ""
            city = ""
            for t in tasks:
                if t.task_type in target_scenes:
                    target = t.params.get("target_job") or target
                    city = t.params.get("city") or city
            skills = [s.get("name") for s in ((profile or {}).get("skills") or []) if s.get("name")][:3]
            keyword_pool = [kw for kw in ([target] if target else []) + skills if kw]
            if not keyword_pool:
                return []
            if not city and profile and profile.get("expect_city"):
                city = profile.get("expect_city")

            # 3. 多关键词并集检索真实岗位
            executor = get_tool_executor()
            fetched: List[Dict[str, Any]] = []
            for kw in keyword_pool[:4]:
                try:
                    r = await executor.execute("job_search", {"keyword": kw, "city": city, "limit": 8})
                    fetched.extend((r.get("data") or {}).get("jobs") or [])
                except Exception:
                    continue
            fetched = self._dedup_jobs(fetched)[:8]
            if not fetched:
                return []

            def _card(j: Dict[str, Any], score=None, reason=""):
                return {
                    "job_id": j.get("job_id"),
                    "title": j.get("title", ""),
                    "company": j.get("company", ""),
                    "city": j.get("city", ""),
                    "salary": j.get("salary", ""),
                    "experience": j.get("experience", ""),
                    "education": j.get("education", ""),
                    "match_score": score,
                    "match_reason": reason,
                }

            # 4. 无简历文本(未登录/没解析好) -> 返回真实岗位, 不带匹配分
            resume_text = self._format_user_profile(profile)
            if not resume_text:
                return [_card(j) for j in fetched]

            # 5. 一次 LLM 挑最值得投的 Top-N(给匹配分与一句理由)
            job_lines = "\n".join(
                f"- {j.get('job_id')}| {j.get('title')} | {j.get('company')} | {j.get('city')} "
                f"| {j.get('salary')} | 经验:{j.get('experience')} | 学历:{j.get('education')}"
                for j in fetched
            )
            prompt = (
                "你是求职顾问。下面是一位求职者的简历要点和一批真实在招岗位(id|岗位|公司|城市|薪资|经验|学历)。\n"
                f"简历要点:\n{resume_text[:800]}\n\n在招岗位:\n{job_lines}\n\n"
                "请挑选最匹配该求职者、最值得投的 ≤5 个岗位(只能从上面列出的 id 里选), 按适合度从高到低排序。\n"
                '严格只输出 JSON: {"items":[{"job_id":123,"score":0到100的整数,"reason":不超过30字的一句投递理由}]}'
            )
            ranked: List[Dict[str, Any]] = []
            try:
                resp = await self.llm.chat(
                    [{"role": "user", "content": prompt}],
                    task_type="resume_match",
                    response_format={"type": "json_object"},
                )
                parsed = json.loads(resp) if isinstance(resp, str) else resp
                ranked = parsed.get("items") or []
            except Exception as e:
                logger.debug(f"推荐岗位打分失败(保留真实岗位不带分): {e}")

            by_id = {j.get("job_id"): j for j in fetched}
            out: List[Dict[str, Any]] = []
            used: set = set()
            for it in ranked:
                jid = it.get("job_id")
                if jid in by_id and jid not in used:
                    out.append(_card(by_id[jid], it.get("score"), (it.get("reason") or "")[:60]))
                    used.add(jid)
            # 打分结果不足时补齐真实岗位(不带分), 保证卡片不为空
            for j in fetched:
                jid = j.get("job_id")
                if jid not in used:
                    out.append(_card(j))
            return out[:6]
        except Exception as e:
            logger.debug(f"构建推荐岗位卡片失败(降级为空): {e}")
            return []

    def _apply_job_context(self, tasks: List[AgentTask],
                           job_context: Optional[Dict[str, Any]],
                           user_profile: Optional[Dict[str, Any]]) -> None:
        """把主站「问顾问」入口的具体岗位(主库某条 JD)注入任务:
        - 已命中 resume_match/skill_gap/learning_path/job_analysis: 目标岗/岗位标题指向该 JD, 附真实 JD 文本;
        - 意图没落成岗位类(general_qa 等): 有简历画像则补一条「与该岗的匹配评估」, 无则补「该岗技能要求分析」。
        """
        if not job_context:
            return
        title = (job_context.get("title") or "").strip()
        desc = (job_context.get("description") or "").strip()
        if not title and not desc:
            return
        meta_bits = [
            title,
            job_context.get("city") or "",
            job_context.get("salary") or "",
            f"经验要求:{job_context.get('experience')}" if job_context.get("experience") else "",
            f"学历要求:{job_context.get('education')}" if job_context.get("education") else "",
        ]
        meta = " · ".join([b for b in meta_bits if b])
        jd_text = (meta + ("\n" + desc if desc else ""))[:1500]

        injected = False
        for t in tasks:
            if t.task_type in ("resume_match", "skill_gap", "learning_path"):
                if title:
                    t.params["target_job"] = title
                t.params["job_jd"] = jd_text
                injected = True
            elif t.task_type == "job_analysis":
                if title:
                    t.params["job_title"] = title
                t.params["job_jd"] = jd_text
                injected = True
        if injected:
            return
        # 在岗位页「问顾问」输入较随意时(多为求职者): 评估匹配优先; 无简历则分析该岗技能要求
        if user_profile:
            tasks.append(AgentTask(
                task_type="resume_match",
                params={
                    "resume_content": self._format_user_profile(user_profile),
                    "target_job": title or "该岗位",
                    "industry": "",
                    "job_jd": jd_text,
                }))
        else:
            tasks.append(AgentTask(
                task_type="job_analysis",
                params={"job_title": title or "该岗位", "industry": "", "job_jd": jd_text}))

    @staticmethod
    def _fetch_facts(db, kw: str) -> str:
        """从主库在招岗位表抓一段可引用的口径数据文本; 失败返回空串。"""
        try:
            s = db.get_job_openings_summary(keyword=kw, top=5)
            total = s.get("total_openings") or 0
            parts = []
            if kw and total:
                parts.append(f"主库在招岗位检索: 关键词「{kw}」命中 {total} 个在招岗位(口径为主库 jobs 真实数据)")
            elif total:
                parts.append(f"主库当前在招岗位共 {total} 个(jobs 表真实数据)")
            ct = s.get("city_top") or []
            if ct:
                parts.append("城市分布(top): " + "、".join(
                    f"{c.get('city')} {c.get('count')}个" for c in ct))
            st = s.get("sample_titles") or []
            if st:
                parts.append("岗位样本: " + "、".join(st[:5]))
            return "\n".join(parts)
        except Exception as e:
            logger.debug(f"抓取平台事实失败: {e}")
            return ""

    def _inject_platform_facts(self, tasks: List[AgentTask]) -> None:
        """给趋势/报告/岗位分析任务附「主库在招岗位」口径数据, 让回答有平台数据并标注来源。"""
        from services.db_service import get_db_service
        db = get_db_service()
        for t in tasks:
            if t.task_type not in ("trend_prediction", "report_generation", "job_analysis"):
                continue
            kw = t.params.get("job_title") or t.params.get("skill") or t.params.get("industry") or ""
            facts = self._fetch_facts(db, str(kw).strip())
            if facts:
                t.params["platform_facts"] = facts

    async def process(
        self,
        user_input: str,
        history: Optional[List[Dict[str, str]]] = None,
        industry: str = "",
        role: str = "",
        request_id: str = "",
        user_profile: Optional[Dict[str, Any]] = None,
        job_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        主入口：处理用户请求

        流程：
        1. 意图识别（带行业/角色上下文）
        2. 置信度阈值检查（低置信度返回澄清追问）
        3. 任务分解（注入行业上下文）
        4. 执行任务（带重试/熔断/超时）
        5. 结果汇总（带校验）

        Args:
            user_input: 用户输入
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]
            industry: 行业上下文
            role: 用户角色 (job_seeker/hr/career_planner/manager)
            request_id: 请求ID，用于全链路追踪
            user_profile: 当前登录用户在主库的最新简历画像(db.get_user_resume_profile 的结果)。
                          resume_match/skill_gap/learning_path 等场景将按真实简历作答;
                          缺省 None 时不注入, 保留原逻辑(用户自述)。
            job_context: 主站「问顾问」入口带来的具体岗位 {job_id,title,city,salary,experience,education,description}。
                         相关任务将按这条真实 JD 作答; 意图没落成岗位类且有简历时补一条对该岗的匹配评估。
        """
        logger.info(f"[{self.name}] 处理用户请求: {user_input[:50]}... (行业: {industry}, 角色: {role})")

        # 启动全链路追踪
        from services.trace_service import get_trace_service
        from services.metrics_service import get_metrics_collector
        trace_svc = get_trace_service()
        metrics = get_metrics_collector()

        trace_id = request_id or str(__import__('uuid').uuid4())[:8]
        trace = trace_svc.start_trace(trace_id, metadata={"input": user_input[:100], "industry": industry})

        # Step 1: 意图识别
        span_intent = trace_svc.start_span(trace_id, "intent_recognition", metadata={"input": user_input[:50]})
        intent_result = await self.recognize_intent(user_input, industry=industry, role=role)
        confidence = intent_result.get("confidence", 0)
        trace_svc.end_span(span_intent, status="completed", error_message="")
        metrics.record_intent(intent_result.get("intent", "unknown"), confidence)
        logger.debug(f"意图识别结果: intent={intent_result.get('intent')}, confidence={confidence}")

        # Step 2: 置信度阈值检查 - 低置信度返回澄清追问
        if confidence < 0.6:
            intent_name = intent_result.get("intent", "general_qa")
            clarification = (
                f"我不太确定您的具体需求。您是想了解某个**岗位的技能要求**，"
                f"还是想评估**自己的能力差距**，或者是想**规划学习路径**？\n\n"
                f"您可以更具体地描述，例如：\n"
                f"- \"Python后端工程师需要什么技能？\"（岗位分析）\n"
                f"- \"我会Java，想转数据分析，差距在哪？\"（差距分析）\n"
                f"- \"如何从前端转全栈？\"（学习路径）"
            )
            trace_svc.end_trace(trace_id, status="completed", error_message="low confidence")
            return {
                "intent": intent_result,
                "tasks": [],
                "results": {},
                "answer": clarification,
                "is_clarification": True,
                "trace_id": trace_id,
            }

        # Step 3: 任务分解（注入行业上下文）
        span_plan = trace_svc.start_span(trace_id, "task_decomposition")
        tasks = await self.decompose_task(intent_result, user_input, industry=industry)
        # 已登录用户且带简历画像: 覆盖 resume_match 等「关于我」任务的简历/技能来源
        self._apply_user_profile(tasks, user_profile)
        # 主站「问顾问」入口带来的具体岗位: 让相关任务按该 JD 作答; 没落成岗位类且有简历则补一条对该岗的匹配评估
        if job_context:
            try:
                self._apply_job_context(tasks, job_context, user_profile)
            except Exception as e:
                logger.debug(f"注入岗位上下文失败(降级): {e}")
        # 趋势/报告/岗位分析: 附主库在招岗位口径数据, 回答引用时标注来源(见 _inject_platform_facts)
        try:
            self._inject_platform_facts(tasks)
        except Exception as e:
            logger.debug(f"注入平台事实失败(降级): {e}")
        trace_svc.end_span(span_plan, status="completed")

        # Step 4: 执行任务
        span_exec = trace_svc.start_span(trace_id, "task_execution", metadata={"task_count": len(tasks)})
        results = await self.execute_tasks(tasks)
        trace_svc.end_span(span_exec, status="completed")

        # Step 5: 结果汇总
        span_summary = trace_svc.start_span(trace_id, "result_summary")
        final_result = await self.summarize_results(
            intent_result.get("intent", "general_qa"),
            results,
            user_input
        )
        trace_svc.end_span(span_summary, status="completed")

        # Step 5.5: 真实岗位结构化推荐(可点卡片)。在耗时预算内尽力取真数据, 失败静默为空, 不阻塞回答
        recommended_jobs: List[Dict[str, Any]] = []
        try:
            recommended_jobs = await self._build_recommended_jobs(tasks, user_profile)
        except Exception as e:
            logger.debug(f"推荐岗位卡片降级为空: {e}")

        # Step 6: 质量评分 - 使用fire-and-forget模式，绝不阻塞响应
        try:
            async def _background_quality_score():
                try:
                    from services.quality_service import get_quality_service
                    quality_svc = get_quality_service()
                    answer_text = str(final_result.get("answer", ""))
                    if answer_text and len(answer_text) > 20:
                        quality_scores = await asyncio.wait_for(
                            quality_svc.auto_score(
                                task_type=intent_result.get("intent", "general_qa"),
                                user_input=user_input,
                                agent_output=answer_text,
                                intent=intent_result.get("intent", ""),
                            ),
                            timeout=10  # 质量评分最多10秒
                        )
                        quality_svc._persist_score(
                            message_id=0, user_id=0, scores=quality_scores,
                        )
                except Exception as e:
                    logger.debug(f"后台质量评分跳过: {e}")

            # fire-and-forget: 不等待质量评分完成
            asyncio.create_task(_background_quality_score())
        except Exception as e:
            logger.debug(f"质量评分跳过: {e}")

        # 结束追踪
        trace_svc.end_trace(trace_id, status="completed")

        # 记录请求级指标
        import time as _time
        elapsed = _time.time() - trace.start_time
        metrics.record_request(200, elapsed)

        return {
            "intent": intent_result,
            "tasks": [t.to_dict() for t in tasks],
            "results": {k: v.to_dict() for k, v in results.items()},
            "trace_id": trace_id,
            "recommended_jobs": recommended_jobs,
            **final_result
        }


# ==================== 会话管理器 ====================

class SessionManager:
    """
    会话管理器 - 内存 + 数据库持久化

    管理：
    - 会话创建/获取/销毁
    - 对话历史（每会话最近N轮）
    - 会话级行业上下文
    - 持久化到数据库（sessions_db + messages表）
    """

    def __init__(self, max_history: int = 20, max_sessions: int = 1000,
                 context_window: int = 10, session_ttl: int = 3600):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._max_history = max_history
        self._max_sessions = max_sessions
        self._context_window = context_window  # 送给LLM的最近N轮对话
        self._session_ttl = session_ttl  # 会话TTL（秒），默认1小时
        self._db = None  # 延迟初始化，避免循环导入

    def _get_db(self):
        """延迟获取数据库服务"""
        if self._db is None:
            try:
                from services.db_service import get_db_service
                self._db = get_db_service()
            except Exception as e:
                logger.warning(f"数据库服务不可用，会话仅内存存储: {e}")
                self._db = None
        return self._db

    def _restore_from_db(self):
        """从数据库恢复会话（启动时调用）"""
        db = self._get_db()
        if not db:
            return

        try:
            db_sessions = db.list_sessions_db(limit=self._max_sessions)
            for s in db_sessions:
                sid = s.get("id", "")
                if sid and sid not in self._sessions:
                    # 从数据库恢复会话元数据
                    self._sessions[sid] = {
                        "id": sid,
                        "user_id": s.get("user_id", 0),
                        "industry": s.get("industry_context", ""),
                        "role": s.get("role", ""),
                        "history": [],
                        "created_at": s.get("created_at", datetime.now().isoformat()),
                    }
                    # 恢复消息历史
                    messages = db.get_session_messages(sid, limit=self._max_history)
                    for msg in messages:
                        self._sessions[sid]["history"].append({
                            "role": msg.get("role", ""),
                            "content": msg.get("content", ""),
                        })

            if db_sessions:
                logger.info(f"从数据库恢复了 {len(db_sessions)} 个会话")
        except Exception as e:
            logger.warning(f"从数据库恢复会话失败: {e}")

    def create_session(self, session_id: Optional[str] = None, industry: str = "",
                       role: str = "", user_id: int = 0) -> str:
        """创建新会话，返回session_id"""
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())[:8]

        self._sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "industry": industry,
            "role": role,
            "history": [],
            "created_at": datetime.now().isoformat(),
        }

        # 持久化到数据库
        db = self._get_db()
        if db:
            try:
                db.create_session_db(session_id, industry=industry, role=role, user_id=user_id)
            except Exception as e:
                logger.warning(f"会话持久化失败: {e}")

        # 超限淘汰最旧会话
        if len(self._sessions) > self._max_sessions:
            oldest_id = min(self._sessions, key=lambda k: self._sessions[k]["created_at"])
            self.destroy_session(oldest_id)

        return session_id

    @staticmethod
    def _uid(v) -> int:
        """统一用户ID为int：JWT sub 是字符串(如"2")，DB INT 列读出是 int 2，
        类型不一致会让所有权判断(owner != user_id)误判，导致续聊重建/历史列表漏会话。
        统一转 int 后比较。"""
        try:
            return int(v) if v is not None else 0
        except (TypeError, ValueError):
            return 0

    def get_session(self, session_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """获取会话（可选校验用户所有权）"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        # 如果提供了user_id，校验所有权（user_id=0表示匿名，跳过校验）
        uid = self._uid(user_id)
        if uid:
            session_owner = self._uid(session.get("user_id", 0))
            if session_owner and session_owner != uid:
                return None  # 不是该用户的会话
        return session

    def add_message(self, session_id: str, role: str, content: str,
                    recommended_jobs: Optional[List[Dict[str, Any]]] = None):
        """添加消息到会话历史。

        recommended_jobs(结构化岗位卡片列表, 仅 assistant 消息带)不进 LLM 上下文
        (history 保持纯文本, 避免卡片撑爆上下文), 但会随消息落库 recommended_jobs 列,
        供前端历史回放时把卡片一并渲染、可再次点击跳转。
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        session["history"].append({"role": role, "content": content})

        # 限制历史长度
        if len(session["history"]) > self._max_history:
            session["history"] = session["history"][-self._max_history:]

        # 持久化消息到数据库
        db = self._get_db()
        if db:
            try:
                _cards_json = None
                if recommended_jobs:
                    _cards_json = json.dumps(recommended_jobs, ensure_ascii=False)
                db.create_message(session_id, role, content, recommended_jobs=_cards_json)
            except Exception as e:
                logger.warning(f"消息持久化失败: {e}")

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取会话历史"""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session["history"]

    def get_industry(self, session_id: str) -> str:
        """获取会话的行业上下文"""
        session = self._sessions.get(session_id)
        if not session:
            return ""
        return session.get("industry", "")

    def set_industry(self, session_id: str, industry: str):
        """设置会话的行业上下文"""
        session = self._sessions.get(session_id)
        if session:
            session["industry"] = industry
            # 同步到数据库
            db = self._get_db()
            if db:
                try:
                    db.update_session_db(session_id, industry=industry)
                except Exception as e:
                    logger.warning(f"会话更新失败: {e}")

    def get_role(self, session_id: str) -> str:
        """获取会话的角色"""
        session = self._sessions.get(session_id)
        if not session:
            return ""
        return session.get("role", "")

    def set_role(self, session_id: str, role: str):
        """设置会话的角色"""
        session = self._sessions.get(session_id)
        if session:
            session["role"] = role
            # 同步到数据库
            db = self._get_db()
            if db:
                try:
                    db.update_session_db(session_id, role=role)
                except Exception as e:
                    logger.warning(f"会话更新失败: {e}")

    def destroy_session(self, session_id: str, user_id: Optional[int] = None) -> bool:
        """销毁会话（可选校验用户所有权）"""
        session = self._sessions.get(session_id)
        if not session:
            return True  # 已不存在，视为成功
        # 如果提供了user_id，校验所有权
        uid = self._uid(user_id)
        if uid:
            session_owner = self._uid(session.get("user_id", 0))
            if session_owner and session_owner != uid:
                return False  # 无权删除
        self._sessions.pop(session_id, None)
        # 从数据库删除
        db = self._get_db()
        if db:
            try:
                db.delete_session_db(session_id)
            except Exception as e:
                logger.warning(f"会话删除失败: {e}")
        return True

    def list_sessions(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出会话（可选按user_id过滤）"""
        sessions = self._sessions.values()
        # 如果提供了user_id（非0），只返回该用户的会话和匿名会话
        uid = self._uid(user_id)
        if uid:
            sessions = [s for s in sessions if self._uid(s.get("user_id", 0)) in (0, uid)]
        return [
            {
                "id": s["id"],
                "user_id": s.get("user_id", 0),
                "industry": s["industry"],
                "role": s.get("role", ""),
                "message_count": len(s["history"]),
                "created_at": s["created_at"],
            }
            for s in sessions
        ]

    def list_messages(self, session_id: str, user_id: Optional[int] = None,
                      limit: int = 200) -> Optional[Dict[str, Any]]:
        """返回某会话的完整历史消息(直接读库, 不受内存上下文窗口限制), 供前端续聊/回看。

        所有权: 传了 user_id(非0) 时只允许本人访问该会话; 匿名会话(user_id=0)任何登录用户可读;
        会话既不在内存也不在库 → 返回 None(视为无权限/不存在), 由路由层转 403。
        返回: {"session_id","user_id","messages":[{id,role,content,intent,created_at}]}
        """
        db = self._get_db()
        if not db:
            return None
        owner = 0
        db_sess = db.get_session_db(session_id) if hasattr(db, "get_session_db") else None
        if db_sess:
            owner = db_sess.get("user_id", 0)
        else:
            mem = self._sessions.get(session_id)
            if not mem:
                return None
            owner = mem.get("user_id", 0)
        # 兼容 JWT sub 为字符串"2" 的情形: 统一按 int 比所有权
        try:
            owner = int(owner)
        except (TypeError, ValueError):
            owner = 0
        try:
            req_uid = int(user_id)
        except (TypeError, ValueError):
            req_uid = user_id
        if req_uid not in (None, 0) and owner != 0 and owner != req_uid:
            return None
        msgs = db.get_session_messages(session_id, limit=limit)
        messages = []
        for m in msgs:
            item = {
                "id": m.get("id"),
                "role": m.get("role", ""),
                "content": m.get("content", ""),
                "intent": m.get("intent", ""),
                "created_at": str(m.get("created_at") or ""),
            }
            # 历史回放: 助理消息当年的真实岗位卡片一并带回(此前设计为"旁路不落库",
            # 用户反馈历史只剩文字、看不到卡片 → 改为随消息落库并回传, 前端可再渲染/再点)
            if m.get("role") == "assistant":
                try:
                    item["recommended_jobs"] = json.loads(m["recommended_jobs"]) if m.get("recommended_jobs") else []
                except Exception:
                    item["recommended_jobs"] = []
            messages.append(item)
        return {"session_id": session_id, "user_id": owner, "messages": messages}

    def get_context_window(self, session_id: str) -> List[Dict[str, str]]:
        """
        获取上下文窗口 — 最近N轮对话作为LLM上下文

        如果历史超过context_window轮，旧消息被压缩为摘要前缀
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        history = session["history"]
        if len(history) <= self._context_window * 2:  # 每轮=user+assistant两条消息
            return history

        # 超出窗口：取最近N轮 + 旧消息摘要
        recent = history[-(self._context_window * 2):]
        old = history[:-(self._context_window * 2)]

        # 如果有旧消息摘要，添加到开头
        summary = session.get("context_summary", "")
        if summary:
            context = [{"role": "system", "content": f"[对话历史摘要] {summary}"}]
        else:
            context = []

        context.extend(recent)
        return context

    async def compress_context(self, session_id: str):
        """
        压缩上下文 — 用LLM将旧消息摘要压缩

        当历史超过2倍context_window时触发
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        history = session["history"]
        threshold = self._context_window * 4  # 超过4倍窗口才压缩

        if len(history) < threshold:
            return

        # 需要压缩的旧消息
        old_messages = history[:threshold // 2]
        old_text = "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:200]}"
            for m in old_messages
        )

        try:
            llm = get_llm_service()
            summary = await llm.chat(
                [
                    {"role": "system", "content": "你是一个对话摘要助手。请将以下对话历史压缩为简洁的摘要，保留关键信息和上下文。"},
                    {"role": "user", "content": f"请摘要以下对话：\n{old_text}"},
                ],
                task_type="intent_classification",  # 用轻量模型做摘要
            )

            # 更新会话
            session["context_summary"] = summary
            # 保留最近的消息
            session["history"] = history[threshold // 2:]
            logger.info(f"上下文压缩完成: session={session_id}, 压缩了{len(old_messages)}条消息")

        except Exception as e:
            logger.warning(f"上下文压缩失败: {e}")

    def cleanup_expired_sessions(self):
        """清理过期会话 — TTL机制"""
        now = datetime.now().timestamp()
        expired = []

        for sid, session in self._sessions.items():
            created = session.get("created_at", "")
            if created:
                try:
                    created_ts = datetime.fromisoformat(created).timestamp()
                    if now - created_ts > self._session_ttl:
                        expired.append(sid)
                except (ValueError, TypeError):
                    pass

        for sid in expired:
            logger.info(f"会话过期清理: {sid}")
            self.destroy_session(sid)

        return len(expired)


# ==================== 工作流引擎 ====================

class WorkflowEngine:
    """
    工作流引擎 - 差异化Agent调用拓扑

    支持：
    - 任务分解
    - 条件路由
    - 链式/并行调用
    - 结果汇总
    """

    def __init__(self):
        self.master = MasterAgent()

    async def execute_workflow(
        self,
        workflow_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行预定义工作流 - 每种类型有差异化的Agent调用拓扑

        Args:
            workflow_type: 工作流类型
            params: 工作流参数

        Returns:
            工作流执行结果
        """
        logger.info(f"[工作流引擎] 执行工作流: {workflow_type}")

        industry = params.get("industry", "")

        if workflow_type == "job_analysis":
            # 场景一：纯岗位分析
            agent = self.master.agents["job_analysis"]
            task = AgentTask(
                task_type="job_analysis",
                params={
                    "job_title": params.get("job_title", params.get("query", "")),
                    "industry": industry,
                }
            )
            result = await agent.execute(task)
            return {
                "workflow": workflow_type,
                "answer": result.data.get("report", "") if result.success else f"分析失败: {result.error}",
                "success": result.success,
            }

        elif workflow_type == "skill_gap":
            # 场景二：能力差距分析（串行链式）
            job_title = params.get("job_title", params.get("query", ""))
            current_skills = params.get("current_skills", [])

            # Step 1: 岗位分析
            ja_agent = self.master.agents["job_analysis"]
            ja_task = AgentTask(
                task_type="job_analysis",
                params={"job_title": job_title, "industry": industry}
            )
            ja_result = await ja_agent.execute(ja_task)

            # Step 2: 差距分析
            sg_agent = self.master.agents["skill_gap"]
            sg_task = AgentTask(
                task_type="skill_gap",
                params={
                    "current_skills": current_skills,
                    "target_job": job_title,
                    "industry": industry,
                    "job_analysis": ja_result.data if ja_result.success else None,
                }
            )
            sg_result = await sg_agent.execute(sg_task)

            return {
                "workflow": workflow_type,
                "job_analysis": ja_result.data if ja_result.success else None,
                "answer": sg_result.data.get("report", "") if sg_result.success else f"差距分析失败: {sg_result.error}",
                "success": sg_result.success,
            }

        elif workflow_type == "learning_path":
            # 场景三：完整学习路径规划（三步串行链式）
            job_title = params.get("job_title", params.get("query", ""))
            current_skills = params.get("current_skills", [])
            target_skills = params.get("target_skills", [])
            time_budget = params.get("time_budget", "3个月")

            # Step 1: 岗位分析
            ja_agent = self.master.agents["job_analysis"]
            ja_task = AgentTask(
                task_type="job_analysis",
                params={"job_title": job_title, "industry": industry}
            )
            ja_result = await ja_agent.execute(ja_task)

            # Step 2: 差距分析
            sg_agent = self.master.agents["skill_gap"]
            sg_task = AgentTask(
                task_type="skill_gap",
                params={
                    "current_skills": current_skills,
                    "target_job": job_title,
                    "industry": industry,
                }
            )
            sg_result = await sg_agent.execute(sg_task)

            # Step 3: 学习路径规划
            lp_agent = self.master.agents["learning_path"]
            lp_task = AgentTask(
                task_type="learning_path",
                params={
                    "current_skills": current_skills,
                    "target_skills": target_skills or [job_title],
                    "time_budget": time_budget,
                    "industry": industry,
                    "gap_analysis": sg_result.data if sg_result.success else None,
                }
            )
            lp_result = await lp_agent.execute(lp_task)

            return {
                "workflow": workflow_type,
                "job_analysis": ja_result.data if ja_result.success else None,
                "skill_gap": sg_result.data if sg_result.success else None,
                "answer": lp_result.data.get("report", "") if lp_result.success else f"学习路径规划失败: {lp_result.error}",
                "success": lp_result.success,
            }

        elif workflow_type == "trend_analysis":
            # 场景四：趋势分析
            agent = self.master.agents["trend_prediction"]
            task = AgentTask(
                task_type="trend_prediction",
                params={
                    "industry": industry or params.get("industry", ""),
                    "skill": params.get("skill", params.get("query", "")),
                    "timeframe": params.get("timeframe", "未来3年"),
                }
            )
            result = await agent.execute(task)
            return {
                "workflow": workflow_type,
                "answer": result.data.get("report", "") if result.success else f"趋势分析失败: {result.error}",
                "success": result.success,
            }

        elif workflow_type == "comprehensive_report":
            # 场景五：综合报告（并行+串行）
            job_title = params.get("job_title", params.get("query", ""))

            # Step 1: 岗位分析与趋势预测并行执行
            ja_task = AgentTask(
                task_type="job_analysis",
                params={"job_title": job_title, "industry": industry}
            )
            tp_task = AgentTask(
                task_type="trend_prediction",
                params={"industry": industry, "skill": job_title, "timeframe": "未来3年"}
            )

            ja_result, tp_result = await asyncio.gather(
                self.master.agents["job_analysis"].execute(ja_task),
                self.master.agents["trend_prediction"].execute(tp_task),
                return_exceptions=True
            )

            # 处理gather异常
            if isinstance(ja_result, Exception):
                ja_result = AgentResult(success=False, error=str(ja_result))
            if isinstance(tp_result, Exception):
                tp_result = AgentResult(success=False, error=str(tp_result))

            # Step 2: 报告生成
            analysis_results = []
            if ja_result.success:
                analysis_results.append(ja_result.data)
            if tp_result.success:
                analysis_results.append(tp_result.data)

            if not analysis_results:
                return {
                    "workflow": workflow_type,
                    "answer": "综合报告生成失败：前置分析均未成功",
                    "success": False,
                }

            rg_agent = self.master.agents["report_generation"]
            rg_task = AgentTask(
                task_type="report_generation",
                params={
                    "analysis_results": analysis_results,
                    "report_type": "综合报告",
                }
            )
            rg_result = await rg_agent.execute(rg_task)

            return {
                "workflow": workflow_type,
                "job_analysis": ja_result.data if ja_result.success else None,
                "trend_prediction": tp_result.data if tp_result.success else None,
                "answer": rg_result.data.get("report", "") if rg_result.success else f"报告生成失败: {rg_result.error}",
                "success": rg_result.success,
            }

        else:
            return {
                "error": f"未知工作流类型: {workflow_type}",
                "supported_types": [
                    "job_analysis", "skill_gap", "learning_path",
                    "trend_analysis", "comprehensive_report"
                ]
            }


# ==================== 单例模式 ====================

_master_agent: Optional[MasterAgent] = None
_workflow_engine: Optional[WorkflowEngine] = None
_session_manager: Optional[SessionManager] = None


def get_master_agent() -> MasterAgent:
    """获取Master Agent单例"""
    global _master_agent
    if _master_agent is None:
        _master_agent = MasterAgent()
    return _master_agent


def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎单例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        # 从数据库恢复会话
        _session_manager._restore_from_db()
    return _session_manager
