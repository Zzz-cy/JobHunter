"""
问答引擎 - 基于RAG的智能问答系统
"""
from typing import List, Dict, Optional, Any
from services.llm_service import get_llm_service
from models.schemas import QueryRequest, QueryResponse
from models.prompts import QA_PROMPT, SKILL_GAP_PROMPT, JOB_MATCH_PROMPT
from utils.logger import get_logger
logger = get_logger("core.qa_engine")


class QAEngine:
    """问答引擎"""

    def __init__(self):
        self.llm = get_llm_service()

    async def answer(
        self,
        question: str,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> QueryResponse:
        """
        通用问答

        Args:
            question: 用户问题
            context: 额外上下文信息
            history: 对话历史

        Returns:
            QueryResponse: 回答结果
        """
        logger.info(f"收到问题: {question[:50]}...")

        # 构建Prompt
        context_str = context or "暂无相关上下文信息"
        prompt = QA_PROMPT.format(
            context=context_str,
            question=question,
        )

        # 构建消息
        messages = []
        if history:
            for h in history[-5:]:  # 只保留最近5轮对话
                messages.append({"role": "user", "content": h.get("user", "")})
                messages.append({"role": "assistant", "content": h.get("assistant", "")})

        messages.append({"role": "user", "content": prompt})

        # 调用大模型
        answer = await self.llm.chat(messages)

        # 动态计算置信度
        confidence = 0.5  # 基线
        if context and context != "暂无相关上下文信息":
            confidence += 0.2  # 有上下文提升置信度
        if len(answer) > 50:
            confidence += 0.1  # 充分的回答
        elif len(answer) < 20:
            confidence -= 0.2  # 过短回答降低置信度
        # 检查不确定性标记
        uncertainty_markers = ["不确定", "可能", "大概", "也许", "无法确定", "不太清楚"]
        if any(marker in answer for marker in uncertainty_markers):
            confidence -= 0.1
        confidence = max(0.1, min(1.0, confidence))  # 限制在 [0.1, 1.0]

        return QueryResponse(
            answer=answer,
            sources=[context_str[:100]] if context else [],
            confidence=round(confidence, 2),
        )

    async def skill_gap_analysis(
        self,
        current_skills: List[str],
        target_job: str,
    ) -> Dict[str, Any]:
        """
        技能差距分析 - 单次LLM调用直接输出JSON

        Args:
            current_skills: 当前掌握的技能
            target_job: 目标岗位

        Returns:
            分析结果
        """
        skills_str = ", ".join(current_skills)
        prompt = f"""请根据用户的当前技能和目标岗位，分析技能差距，以JSON格式输出。

用户当前技能: {skills_str}
目标岗位: {target_job}

请输出以下JSON格式：
{{
    "advantages": ["已具备的优势技能1", "优势技能2"],
    "gaps": ["需要补充的技能1", "需要补充的技能2"],
    "learning_path": ["建议学习顺序1", "学习顺序2", "学习顺序3"],
    "estimated_time": "预计达到目标所需时间"
}}

只输出JSON，不要其他内容。"""

        result = await self.llm.extract_json(prompt, task_type="skill_gap")
        if "error" in result:
            return {
                "analysis": result.get("raw", ""),
                "current_skills": current_skills,
                "target_job": target_job,
            }
        return result

    async def job_match(
        self,
        job_info: str,
        candidate_info: str,
    ) -> Dict[str, Any]:
        """
        岗位匹配度评估 - 单次LLM调用直接输出JSON

        Args:
            job_info: 岗位信息
            candidate_info: 候选人信息

        Returns:
            匹配度评估结果
        """
        prompt = f"""请评估候选人与岗位的匹配度，以JSON格式输出。

岗位信息: {job_info}
候选人信息: {candidate_info}

请输出以下JSON格式：
{{
    "skill_match": 85,
    "experience_match": 70,
    "education_match": 80,
    "overall_match": 78,
    "advantages": ["匹配优势1", "匹配优势2"],
    "risks": ["潜在风险1", "潜在风险2"],
    "interview_suggestions": ["面试建议1", "面试建议2"]
}}

每项匹配度评分为0-100分。只输出JSON，不要其他内容。"""

        result = await self.llm.extract_json(prompt, task_type="skill_gap")
        if "error" in result:
            return {
                "assessment": result.get("raw", ""),
                "job_info": job_info,
                "candidate_info": candidate_info,
            }
        return result

    async def stream_answer(
        self,
        question: str,
        context: Optional[str] = None,
    ):
        """
        流式问答 - 用于SSE

        Args:
            question: 用户问题
            context: 上下文信息

        Yields:
            文本片段
        """
        context_str = context or "暂无相关上下文信息"
        prompt = QA_PROMPT.format(
            context=context_str,
            question=question,
        )

        messages = [
            {"role": "system", "content": "你是一位专业的人力资源智能助手。"},
            {"role": "user", "content": prompt},
        ]

        async for chunk in self.llm.chat_stream(messages):
            yield chunk


# 单例
_qa_engine: Any = None


def get_qa_engine() -> QAEngine:
    """获取问答引擎单例"""
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = QAEngine()
    return _qa_engine
