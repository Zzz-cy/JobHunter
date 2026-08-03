"""
质量评分服务 - 自动评分与事实核查
"""
from __future__ import annotations

import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.config import QUOTA_CONFIG
from utils.logger import get_logger
logger = get_logger("services.quality_service")

# 幻觉标记词
HALLUCINATION_MARKERS = [
    "据我所知", "据传", "有人说", "可能", "也许",
    "我猜测", "大概", "似乎", "好像", "应该",
    "不一定", "不确定", "未经验证",
]


class QualityService:
    """质量评分服务 - 规则评分 + LLM-as-Judge + 事实核查"""

    def __init__(self):
        self._llm = None  # 懒加载
        self._db = None   # 懒加载

    def _get_llm(self):
        """懒加载LLM服务"""
        if self._llm is None:
            from services.llm_service import get_llm_service
            self._llm = get_llm_service()
        return self._llm

    def _get_db(self):
        """懒加载数据库服务"""
        if self._db is None:
            from services.db_service import get_db_service
            self._db = get_db_service()
        return self._db

    async def auto_score(self, task_type: str, user_input: str, agent_output: str,
                         intent: str = "") -> Dict[str, Any]:
        """
        自动质量评分

        Returns:
            {
                "auto_score": float (0-5),
                "intent_accuracy": float (0-1),
                "task_completion": float (0-1),
                "response_quality": float (0-1),
                "fact_check_summary": str,
            }
        """
        # 1. 规则评分
        rule_scores = self._rule_based_score(task_type, agent_output)

        # 2. LLM-as-Judge评分（可选，可能失败）
        llm_score = 0.0
        try:
            llm_score = await self._llm_judge_score(user_input, agent_output)
        except Exception as e:
            logger.warning(f"LLM评分失败: {e}")

        # 3. 事实核查（可选）
        fact_check_summary = ""
        try:
            fact_result = await self.fact_check(agent_output)
            if fact_result.get("contradictions", 0) > 0:
                fact_check_summary = f"发现{fact_result['contradictions']}个矛盾"
            elif fact_result.get("unverified_claims", 0) > 0:
                fact_check_summary = f"{fact_result['unverified_claims']}个声明未验证"
            else:
                fact_check_summary = "关键声明已验证"
        except Exception:
            fact_check_summary = "事实核查未执行"

        # 综合评分
        rule_avg = (rule_scores["length_score"] + rule_scores["structure_score"] +
                    rule_scores["hallucination_score"]) / 3.0
        # LLM评分权重0.4，规则评分权重0.6
        auto_score = rule_avg * 3.0 + llm_score * 2.0
        auto_score = max(0.0, min(5.0, auto_score))

        # 意图准确度（基于规则推断）
        intent_accuracy = rule_scores.get("intent_accuracy", 0.7)

        # 任务完成度
        task_completion = rule_scores.get("task_completion", 0.7)

        # 响应质量
        response_quality = rule_scores.get("response_quality", 0.7)

        return {
            "auto_score": round(auto_score, 2),
            "intent_accuracy": round(intent_accuracy, 2),
            "task_completion": round(task_completion, 2),
            "response_quality": round(response_quality, 2),
            "fact_check_summary": fact_check_summary,
        }

    async def fact_check(self, agent_output: str, knowledge_context: str = "") -> Dict[str, Any]:
        """
        事实核查 - 提取关键声明并与知识库交叉验证

        Returns:
            {"verified_claims": int, "unverified_claims": int,
             "contradictions": int, "details": list}
        """
        # 从输出中提取可能的声明（简单启发式）
        claims = self._extract_claims(agent_output)

        if not claims:
            return {
                "verified_claims": 0,
                "unverified_claims": 0,
                "contradictions": 0,
                "details": [],
            }

        verified = 0
        unverified = 0
        contradictions = 0
        details = []

        # 对每个声明尝试RAG检索验证
        try:
            from services.rag_service import get_rag_service
            rag = get_rag_service()

            for claim in claims[:5]:  # 最多验证5个声明
                try:
                    result = await rag.query(claim, top_k=2)
                    if isinstance(result, dict):
                        sources = result.get("sources", [])
                        if sources:
                            verified += 1
                            details.append({"claim": claim, "status": "verified"})
                        else:
                            unverified += 1
                            details.append({"claim": claim, "status": "unverified"})
                    else:
                        unverified += 1
                        details.append({"claim": claim, "status": "unverified"})
                except Exception:
                    unverified += 1
                    details.append({"claim": claim, "status": "unverified"})
        except Exception as e:
            logger.warning(f"事实核查失败: {e}")
            unverified = len(claims)

        return {
            "verified_claims": verified,
            "unverified_claims": unverified,
            "contradictions": contradictions,
            "details": details,
        }

    def _extract_claims(self, text: str) -> List[str]:
        """从文本中提取可能的声明（简单启发式）"""
        claims = []

        # 提取包含数值的句子（可能是薪资、比例等事实声明）
        sentences = re.split(r'[。！？\n]', text)
        for s in sentences:
            s = s.strip()
            if not s or len(s) < 5:
                continue
            # 包含数字的事实声明
            if re.search(r'\d+[%万千元]', s):
                claims.append(s)
            # 包含技能名的声明
            elif re.search(r'[需要|要求|掌握|熟练].*[技能|技术|工具|语言]', s):
                claims.append(s)

        return claims[:10]  # 最多10个声明

    def _rule_based_score(self, task_type: str, output: str) -> Dict[str, float]:
        """
        规则评分 - 基于长度、结构、幻觉标记等启发式评分

        Returns:
            {length_score, structure_score, hallucination_score,
             intent_accuracy, task_completion, response_quality}
        """
        if not output:
            return {
                "length_score": 0.0,
                "structure_score": 0.0,
                "hallucination_score": 0.5,
                "intent_accuracy": 0.3,
                "task_completion": 0.1,
                "response_quality": 0.1,
            }

        # 长度评分
        length = len(output)
        if length < 50:
            length_score = 0.3
        elif length < 200:
            length_score = 0.6
        elif length < 1000:
            length_score = 0.9
        else:
            length_score = 1.0

        # 结构评分（是否有分段、列表等）
        has_structure = bool(re.search(r'[1-9][.、）)]|[-•*]\s|#{1,3}\s|步骤|阶段|第一', output))
        structure_score = 0.9 if has_structure else 0.5

        # 幻觉检测评分
        hallucination_count = sum(1 for marker in HALLUCINATION_MARKERS if marker in output)
        if hallucination_count == 0:
            hallucination_score = 1.0
        elif hallucination_count <= 2:
            hallucination_score = 0.7
        else:
            hallucination_score = 0.4

        # 综合推断
        intent_accuracy = min(1.0, 0.5 + length_score * 0.3 + hallucination_score * 0.2)
        task_completion = min(1.0, 0.4 + length_score * 0.3 + structure_score * 0.3)
        response_quality = min(1.0, 0.4 + hallucination_score * 0.3 + structure_score * 0.3)

        return {
            "length_score": length_score,
            "structure_score": structure_score,
            "hallucination_score": hallucination_score,
            "intent_accuracy": intent_accuracy,
            "task_completion": task_completion,
            "response_quality": response_quality,
        }

    async def _llm_judge_score(self, user_input: str, agent_output: str) -> float:
        """
        LLM-as-Judge评分 - 使用轻量模型对输出质量打分

        Returns:
            1-5分
        """
        llm = self._get_llm()

        prompt = f"""请对以下AI助手的回答质量打分（1-5分）。

用户问题: {user_input[:300]}
AI回答: {agent_output[:500]}

评分标准:
1分: 完全不相关或错误
2分: 部分相关但信息不足
3分: 基本相关但不完整
4分: 相关且较完整
5分: 完全相关、准确、完整

请只回复一个1-5的数字。"""

        try:
            result = await llm.chat(
                [{"role": "user", "content": prompt}],
                task_type="intent_classification",
            )
            # 提取数字
            score_match = re.search(r'[1-5]', result)
            if score_match:
                return float(score_match.group())
            return 3.0  # 默认中等分数
        except Exception as e:
            logger.warning(f"LLM评分失败: {e}")
            return 3.0

    def _persist_score(self, message_id: int, user_id: int, scores: Dict[str, Any]) -> int:
        """持久化评分到evaluations表"""
        db = self._get_db()
        try:
            eval_id = db.create_evaluation(
                message_id=message_id,
                user_id=user_id,
                auto_score=scores.get("auto_score", 0),
                intent_accuracy=scores.get("intent_accuracy", 0),
                task_completion=scores.get("task_completion", 0),
                response_quality=scores.get("response_quality", 0),
            )
            return eval_id
        except Exception as e:
            logger.warning(f"评分持久化失败: {e}")
            return 0


# 单例
_quality_service: Any = None


def get_quality_service() -> QualityService:
    """获取质量评分服务单例"""
    global _quality_service
    if _quality_service is None:
        _quality_service = QualityService()
    return _quality_service
