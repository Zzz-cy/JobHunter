"""
低分反馈优化服务 - 自动归类失败原因、生成Prompt改进建议、测试集扩充
"""
from __future__ import annotations

import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import get_logger
logger = get_logger("services.feedback_optimizer")


class FeedbackOptimizer:
    """低分反馈优化服务"""

    def __init__(self):
        self._llm = None
        self._db = None

    def _get_llm(self):
        if self._llm is None:
            from services.llm_service import get_llm_service
            self._llm = get_llm_service()
        return self._llm

    def _get_db(self):
        if self._db is None:
            from services.db_service import get_db_service
            self._db = get_db_service()
        return self._db

    # ========== 失败原因归类 ==========

    FAILURE_CATEGORIES = {
        "intent_error": "意图识别错误",
        "task_planning_error": "任务规划不当",
        "llm_quality_error": "LLM输出质量差",
        "tool_call_error": "工具调用失败",
        "context_missing": "上下文缺失",
        "factual_error": "事实错误",
    }

    async def classify_failure(self, query: str, agent_output: str,
                                user_score: float = 0, auto_score: float = 0,
                                intent: str = "") -> Dict[str, Any]:
        """
        自动归类失败原因

        Returns:
            {primary_cause, secondary_cause, confidence, reasoning, suggestions}
        """
        llm = self._get_llm()

        prompt = f"""分析以下低分AI回答的失败原因，并归类到以下类别之一：
- intent_error: 意图识别错误（AI误解了用户意图）
- task_planning_error: 任务规划不当（Agent选择或流程有误）
- llm_quality_error: LLM输出质量差（回答模糊、不完整、幻觉）
- tool_call_error: 工具调用失败（知识库/图谱/数据库查询失败）
- context_missing: 上下文缺失（缺少必要背景信息）
- factual_error: 事实错误（输出包含错误的事实信息）

用户问题: {query[:300]}
AI回答: {agent_output[:500]}
用户评分: {user_score}/5, 自动评分: {auto_score}/5
识别意图: {intent}

请以JSON格式回复:
{{
    "primary_cause": "主要失败类别",
    "secondary_cause": "次要失败类别（可null）",
    "confidence": 0.8,
    "reasoning": "判断理由",
    "suggestions": ["改进建议1", "改进建议2"]
}}"""

        try:
            result = await llm.extract_json(
                prompt,
                task_type="intent_classification",
            )
            return {
                "primary_cause": result.get("primary_cause", "llm_quality_error"),
                "secondary_cause": result.get("secondary_cause"),
                "confidence": result.get("confidence", 0.6),
                "reasoning": result.get("reasoning", ""),
                "suggestions": result.get("suggestions", []),
            }
        except Exception as e:
            logger.warning(f"失败归类失败: {e}")
            # 回退到规则判断
            return self._rule_based_classify(query, agent_output, user_score, auto_score, intent)

    def _rule_based_classify(self, query: str, output: str, user_score: float,
                              auto_score: float, intent: str) -> Dict[str, Any]:
        """规则判断失败原因"""
        suggestions = []

        # 检查意图匹配
        intent_keywords = {
            "job_analysis": ["岗位", "技能", "要求"],
            "skill_gap": ["差距", "不足", "欠缺"],
            "learning_path": ["学习", "路径", "规划"],
            "trend_prediction": ["趋势", "预测", "未来"],
            "job_compare": ["对比", "比较", "差异"],
            "resume_match": ["匹配", "简历", "适合"],
            "report_generation": ["报告", "总结", "概览"],
        }

        keywords = intent_keywords.get(intent, [])
        if keywords:
            matches = sum(1 for kw in keywords if kw in output)
            if matches == 0:
                return {
                    "primary_cause": "intent_error",
                    "secondary_cause": None,
                    "confidence": 0.7,
                    "reasoning": f"输出中无意图'{intent}'相关关键词",
                    "suggestions": ["优化意图识别prompt", "增加意图确认步骤"],
                }

        # 检查输出长度
        if len(output) < 50:
            suggestions.append("增加输出最小长度要求")
            return {
                "primary_cause": "llm_quality_error",
                "secondary_cause": None,
                "confidence": 0.8,
                "reasoning": "输出过短，可能未完整生成",
                "suggestions": suggestions or ["增加输出最小长度校验"],
            }

        # 检查幻觉标记
        hallucination_markers = ["据我所知", "可能", "也许", "大概", "似乎"]
        hallucination_count = sum(1 for m in hallucination_markers if m in output)
        if hallucination_count >= 3:
            suggestions.append("增加事实核查步骤")
            return {
                "primary_cause": "factual_error",
                "secondary_cause": "llm_quality_error",
                "confidence": 0.6,
                "reasoning": f"输出包含{hallucination_count}个不确定性标记",
                "suggestions": suggestions or ["增强事实核查"],
            }

        return {
            "primary_cause": "llm_quality_error",
            "secondary_cause": None,
            "confidence": 0.5,
            "reasoning": "默认归类为LLM输出质量差",
            "suggestions": ["优化prompt模板", "调整模型参数"],
        }

    # ========== Prompt优化建议 ==========

    async def generate_prompt_suggestions(self, failure_cause: str, query: str,
                                          output: str, intent: str = "") -> List[str]:
        """
        根据失败模式生成Prompt改进建议

        Returns:
            改进建议列表
        """
        # 基于失败原因的模板建议
        template_suggestions = {
            "intent_error": [
                "在意图识别prompt中增加更多示例",
                "添加意图确认步骤（confidence < 0.6时追问）",
                "增加行业上下文到意图识别prompt",
            ],
            "task_planning_error": [
                "优化任务分解规则，增加更多意图-任务映射",
                "增加任务依赖检查逻辑",
                "添加回退策略（子任务失败时尝试替代方案）",
            ],
            "llm_quality_error": [
                "增加输出格式约束（强制JSON/Markdown结构）",
                "添加Few-shot示例到prompt",
                "提高temperature精度（降低到0.1-0.2）",
                "增加输出最小长度要求",
            ],
            "tool_call_error": [
                "优化工具选择prompt，增加工具描述细节",
                "添加工具调用失败后的降级策略",
                "增加工具参数校验",
            ],
            "context_missing": [
                "增加RAG检索步骤，注入更多背景知识",
                "在prompt中增加行业知识前缀",
                "扩展知识库覆盖范围",
            ],
            "factual_error": [
                "添加事实核查步骤（RAG交叉验证）",
                "降低temperature到0.1",
                '增加"如果不确定请说明"的指令',
            ],
        }

        return template_suggestions.get(failure_cause, ["通用优化：增加prompt细节和示例"])

    # ========== 测试集扩充 ==========

    async def expand_test_set(self, low_score_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将低分样本转化为测试用例

        Args:
            low_score_samples: 低分评价记录列表

        Returns:
            新增测试用例列表
        """
        new_cases = []

        for sample in low_score_samples:
            # 从低分评价中提取信息
            query = sample.get("query", sample.get("user_feedback", ""))
            if not query or len(query) < 5:
                continue

            intent = sample.get("intent", "general_qa")
            industry = sample.get("industry", "")

            # 使用LLM提取期望关键词和实体
            try:
                llm = self._get_llm()
                prompt = f"""从以下用户问题中提取：
1. 期望AI回答中应包含的关键词（3-5个）
2. 期望AI回答中应包含的实体名（2-3个）

用户问题: {query[:200]}

请以JSON格式回复:
{{"expected_keywords": ["关键词1", "关键词2"], "expected_entities": ["实体1", "实体2"]}}"""

                result = await llm.extract_json(
                    prompt,
                    task_type="intent_classification",
                )

                new_case = {
                    "id": f"auto_{len(new_cases) + 1}",
                    "intent": intent,
                    "query": query,
                    "expected_keywords": result.get("expected_keywords", []),
                    "expected_entities": result.get("expected_entities", []),
                    "industry": industry,
                    "source": "low_score_sample",
                }
                new_cases.append(new_case)

            except Exception as e:
                logger.warning(f"测试用例生成失败: {e}")
                # 简单回退
                new_cases.append({
                    "id": f"auto_{len(new_cases) + 1}",
                    "intent": intent,
                    "query": query,
                    "expected_keywords": [],
                    "expected_entities": [],
                    "industry": industry,
                    "source": "low_score_sample",
                })

        return new_cases

    # ========== 模型路由优化建议 ==========

    def analyze_model_performance(self) -> Dict[str, Any]:
        """
        分析各模型在不同任务上的表现，给出路由优化建议

        Returns:
            {model_stats: {model: {task: {avg_score, count}}}, suggestions: [...]}
        """
        db = self._get_db()
        try:
            # 从evaluations + agent_executions关联查询
            db.cursor.execute(db._q("""
                SELECT ae.model_used, ae.task_type, ae.status,
                       AVG(e.auto_score) as avg_score,
                       COUNT(*) as count
                FROM agent_executions ae
                LEFT JOIN evaluations e ON e.message_id = 0
                GROUP BY ae.model_used, ae.task_type, ae.status
                ORDER BY ae.model_used, ae.task_type
            """))
            rows = [dict(row) for row in db.cursor.fetchall()]
        except Exception as e:
            logger.warning(f"模型性能分析查询失败: {e}")
            rows = []

        model_stats = {}
        suggestions = []

        for row in rows:
            model = row.get("model_used", "unknown")
            task = row.get("task_type", "unknown")
            if model not in model_stats:
                model_stats[model] = {}
            model_stats[model][task] = {
                "avg_score": row.get("avg_score", 0),
                "count": row.get("count", 0),
                "status": row.get("status", ""),
            }

        # 生成优化建议
        for model, tasks in model_stats.items():
            for task, stats in tasks.items():
                avg_score = stats.get("avg_score", 0)
                if avg_score > 0 and avg_score < 2.5:
                    suggestions.append(
                        f"模型 {model} 在任务 {task} 上持续低分(avg={avg_score:.1f})，"
                        f"建议切换到更合适的模型"
                    )

        return {
            "model_stats": model_stats,
            "suggestions": suggestions,
        }

    # ========== 优化效果验证 ==========

    async def verify_improvement(self, before_scores: Dict[str, float],
                                 after_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        验证优化效果

        Returns:
            {improved, dimension_changes, summary}
        """
        improved = True
        changes = {}

        for dim in ["intent_accuracy", "task_completion", "fact_accuracy",
                     "structure_quality", "relevance", "completeness", "overall_score"]:
            before = before_scores.get(dim, 0)
            after = after_scores.get(dim, 0)
            diff = after - before
            changes[dim] = {
                "before": round(before, 3),
                "after": round(after, 3),
                "diff": round(diff, 3),
                "improved": diff > 0,
            }
            if dim == "overall_score" and diff < 0:
                improved = False

        overall_diff = changes.get("overall_score", {}).get("diff", 0)
        return {
            "improved": improved,
            "dimension_changes": changes,
            "summary": f"综合评分变化: {overall_diff:+.3f} ({'提升' if overall_diff > 0 else '下降'})",
        }


# 单例
_feedback_optimizer: Any = None


def get_feedback_optimizer() -> FeedbackOptimizer:
    """获取反馈优化服务单例"""
    global _feedback_optimizer
    if _feedback_optimizer is None:
        _feedback_optimizer = FeedbackOptimizer()
    return _feedback_optimizer
