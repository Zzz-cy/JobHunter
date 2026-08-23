"""
自动化评价服务 - 评价维度定义、自动评分引擎、批量评价流水线
"""
from __future__ import annotations

import json
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from utils.logger import get_logger
logger = get_logger("services.evaluation_service")


# ==================== 评价维度定义 ====================

@dataclass
class EvaluationDimensions:
    """评价维度定义"""
    # 意图准确率：识别的意图是否是用户真实意图
    intent_accuracy: float = 0.0  # 0-1
    # 任务完成度：是否完整回答了用户问题
    task_completion: float = 0.0  # 0-1
    # 事实准确率：输出中的事实是否可验证
    fact_accuracy: float = 0.0  # 0-1
    # 结构化质量：JSON输出是否符合schema
    structure_quality: float = 0.0  # 0-1
    # 响应相关性：回答是否与问题相关
    relevance: float = 0.0  # 0-1
    # 信息完整度：是否遗漏关键信息
    completeness: float = 0.0  # 0-1
    # 综合评分
    overall_score: float = 0.0  # 0-5

    def to_dict(self) -> Dict[str, float]:
        return {
            "intent_accuracy": round(self.intent_accuracy, 3),
            "task_completion": round(self.task_completion, 3),
            "fact_accuracy": round(self.fact_accuracy, 3),
            "structure_quality": round(self.structure_quality, 3),
            "relevance": round(self.relevance, 3),
            "completeness": round(self.completeness, 3),
            "overall_score": round(self.overall_score, 2),
        }


@dataclass
class TestCase:
    """标准测试用例"""
    id: str = ""
    intent: str = ""
    query: str = ""
    expected_keywords: List[str] = field(default_factory=list)
    expected_entities: List[str] = field(default_factory=list)
    industry: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intent": self.intent,
            "query": self.query,
            "expected_keywords": self.expected_keywords,
            "expected_entities": self.expected_entities,
            "industry": self.industry,
        }


@dataclass
class BatchResult:
    """批量评价结果"""
    test_case_id: str = ""
    dimensions: EvaluationDimensions = field(default_factory=EvaluationDimensions)
    actual_output: str = ""
    passed: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "dimensions": self.dimensions.to_dict(),
            "actual_output": self.actual_output[:200],
            "passed": self.passed,
            "error": self.error,
        }


# ==================== 标准测试集 ====================

DEFAULT_TEST_SET: List[Dict[str, Any]] = [
    # job_analysis 测试用例
    {"id": "ja_1", "intent": "job_analysis", "query": "Python后端开发需要什么技能？",
     "expected_keywords": ["Python", "后端", "开发"], "expected_entities": ["Python"], "industry": "it"},
    {"id": "ja_2", "intent": "job_analysis", "query": "金融分析师需要哪些能力？",
     "expected_keywords": ["金融", "分析"], "expected_entities": ["金融分析师"], "industry": "finance"},
    {"id": "ja_3", "intent": "job_analysis", "query": "临床医生的技能要求是什么？",
     "expected_keywords": ["临床", "医疗"], "expected_entities": ["临床医生"], "industry": "healthcare"},
    # skill_gap 测试用例
    {"id": "sg_1", "intent": "skill_gap", "query": "我会Java，想转数据分析，差什么？",
     "expected_keywords": ["Java", "数据分析", "差距"], "expected_entities": ["Java", "数据分析"], "industry": "it"},
    {"id": "sg_2", "intent": "skill_gap", "query": "从护士转行做健康管理师需要补什么？",
     "expected_keywords": ["护士", "健康管理"], "expected_entities": ["护士", "健康管理师"], "industry": "healthcare"},
    # learning_path 测试用例
    {"id": "lp_1", "intent": "learning_path", "query": "如何从前端转全栈开发？",
     "expected_keywords": ["前端", "全栈", "学习", "路径"], "expected_entities": ["前端", "全栈"], "industry": "it"},
    # trend_prediction 测试用例
    {"id": "tp_1", "intent": "trend_prediction", "query": "AI行业未来什么技能最重要？",
     "expected_keywords": ["AI", "趋势", "技能"], "expected_entities": ["AI"], "industry": "it"},
    # job_compare 测试用例
    {"id": "jc_1", "intent": "job_compare", "query": "前端和后端的技能要求有什么不同？",
     "expected_keywords": ["前端", "后端", "对比"], "expected_entities": ["前端", "后端"], "industry": "it"},
    # resume_match 测试用例
    {"id": "rm_1", "intent": "resume_match", "query": "我的简历适合投哪些岗位？我有3年Java经验",
     "expected_keywords": ["简历", "Java", "匹配"], "expected_entities": ["Java"], "industry": "it"},
    # report_generation 测试用例
    {"id": "rg_1", "intent": "report_generation", "query": "帮我出一份数据分析行业报告",
     "expected_keywords": ["报告", "数据分析"], "expected_entities": ["数据分析"], "industry": "it"},
    # general_qa 测试用例
    {"id": "gq_1", "intent": "general_qa", "query": "什么是微服务架构？",
     "expected_keywords": ["微服务", "架构"], "expected_entities": ["微服务"], "industry": "it"},
    {"id": "gq_2", "intent": "general_qa", "query": "六西格玛是什么？",
     "expected_keywords": ["六西格玛"], "expected_entities": ["六西格玛"], "industry": "manufacturing"},
]


class EvaluationService:
    """自动化评价服务"""

    def __init__(self):
        self._llm = None
        self._db = None
        self._test_set: List[TestCase] = []
        self._load_default_test_set()

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

    def _load_default_test_set(self):
        """加载默认测试集"""
        for item in DEFAULT_TEST_SET:
            self._test_set.append(TestCase(
                id=item.get("id", ""),
                intent=item.get("intent", "general_qa"),
                query=item.get("query", ""),
                expected_keywords=item.get("expected_keywords", []),
                expected_entities=item.get("expected_entities", []),
                industry=item.get("industry", "it"),
            ))

    def load_test_set(self, test_cases: List[Dict[str, Any]]) -> int:
        """加载自定义测试集"""
        self._test_set = []
        for item in test_cases:
            self._test_set.append(TestCase(
                id=item.get("id", str(len(self._test_set))),
                intent=item.get("intent", "general_qa"),
                query=item.get("query", ""),
                expected_keywords=item.get("expected_keywords", []),
                expected_entities=item.get("expected_entities", []),
                industry=item.get("industry", "it"),
            ))
        return len(self._test_set)

    def get_test_set(self) -> List[Dict[str, Any]]:
        """获取当前测试集"""
        return [tc.to_dict() for tc in self._test_set]

    # ========== 自动评分引擎 ==========

    async def evaluate_single(self, query: str, agent_output: str,
                              intent: str = "", expected_keywords: List[str] = None,
                              expected_entities: List[str] = None) -> EvaluationDimensions:
        """
        对单条Agent输出进行多维度评分

        Args:
            query: 用户查询
            agent_output: Agent输出
            intent: 识别的意图
            expected_keywords: 期望关键词
            expected_entities: 期望实体

        Returns:
            EvaluationDimensions 各维度评分
        """
        dims = EvaluationDimensions()

        if not agent_output or not query:
            return dims

        # 1. 意图准确率（基于关键词匹配推断）
        dims.intent_accuracy = self._score_intent_accuracy(query, agent_output, intent)

        # 2. 任务完成度
        dims.task_completion = await self._score_task_completion(query, agent_output)

        # 3. 事实准确率
        dims.fact_accuracy = await self._score_fact_accuracy(agent_output)

        # 4. 结构化质量
        dims.structure_quality = self._score_structure_quality(agent_output)

        # 5. 响应相关性
        dims.relevance = await self._score_relevance(query, agent_output)

        # 6. 信息完整度
        dims.completeness = self._score_completeness(
            agent_output, expected_keywords or [], expected_entities or []
        )

        # 综合评分 = 加权平均 (0-5分)
        dims.overall_score = (
            dims.intent_accuracy * 0.2 +
            dims.task_completion * 0.25 +
            dims.fact_accuracy * 0.15 +
            dims.structure_quality * 0.1 +
            dims.relevance * 0.2 +
            dims.completeness * 0.1
        ) * 5.0

        return dims

    def _score_intent_accuracy(self, query: str, output: str, intent: str) -> float:
        """意图准确率评分（启发式）"""
        if not intent:
            return 0.5
        # 基本检查：输出是否与意图相关
        intent_keywords = {
            "job_analysis": ["岗位", "职位", "技能要求", "能力要求", "任职"],
            "skill_gap": ["差距", "不足", "缺失", "需要提升", "欠缺"],
            "learning_path": ["学习", "路径", "规划", "阶段", "课程"],
            "trend_prediction": ["趋势", "未来", "发展", "预测", "前景"],
            "job_compare": ["对比", "差异", "区别", "不同", "比较"],
            "resume_match": ["匹配", "适合", "简历", "投递", "契合"],
            "report_generation": ["报告", "分析", "总结", "概览"],
            "general_qa": [],
        }
        keywords = intent_keywords.get(intent, [])
        if not keywords:
            return 0.7  # 通用问答不容易判断
        matches = sum(1 for kw in keywords if kw in output)
        if matches >= 2:
            return 1.0
        elif matches >= 1:
            return 0.8
        return 0.5

    async def _score_task_completion(self, query: str, output: str) -> float:
        """任务完成度评分（LLM评判）"""
        if len(output) < 20:
            return 0.2
        try:
            llm = self._get_llm()
            prompt = f"""评估以下AI回答是否完整地回答了用户问题。

用户问题: {query[:200]}
AI回答: {output[:300]}

请只回复一个0到1之间的数字，表示完成度（0=完全没回答，1=完全回答）。"""
            result = await llm.chat(
                [{"role": "user", "content": prompt}],
                task_type="intent_classification",
            )
            match = re.search(r'[0-9]*\.?[0-9]+', result)
            if match:
                score = float(match.group())
                return max(0.0, min(1.0, score))
        except Exception as e:
            logger.debug(f"任务完成度评分失败: {e}")
        # 回退到启发式
        return min(1.0, 0.3 + len(output) / 1000.0)

    async def _score_fact_accuracy(self, output: str) -> float:
        """事实准确率评分（RAG交叉验证）"""
        try:
            from services.rag_service import get_rag_service
            rag = get_rag_service()
            # 提取声明并验证
            claims = re.findall(r'[一-鿿]+[\d]+[%万千]?', output)
            if not claims:
                return 0.8  # 无明确事实声明的默认分
            verified = 0
            for claim in claims[:3]:
                try:
                    result = await rag.query(claim, top_k=1)
                    if isinstance(result, dict) and result.get("sources"):
                        verified += 1
                except Exception:
                    pass
            return verified / min(len(claims), 3) if claims else 0.8
        except Exception:
            return 0.7  # RAG不可用时的默认分

    def _score_structure_quality(self, output: str) -> float:
        """结构化质量评分（规则检查）"""
        score = 0.0
        # 有分段标题
        if re.search(r'#{1,3}\s|第[一二三四五六七八九十]+[章节部分]', output):
            score += 0.3
        # 有列表
        if re.search(r'[1-9][.、）)]|[-•*]\s', output):
            score += 0.3
        # 有加粗/高亮
        if '**' in output or '==' in output:
            score += 0.2
        # 长度合理（>200字的结构化输出）
        if len(output) > 200:
            score += 0.2
        return min(1.0, score)

    async def _score_relevance(self, query: str, output: str) -> float:
        """响应相关性评分（LLM评判）"""
        try:
            llm = self._get_llm()
            prompt = f"""评估以下AI回答与用户问题的相关程度。

用户问题: {query[:200]}
AI回答: {output[:300]}

请只回复一个0到1之间的数字，表示相关性（0=完全无关，1=高度相关）。"""
            result = await llm.chat(
                [{"role": "user", "content": prompt}],
                task_type="intent_classification",
            )
            match = re.search(r'[0-9]*\.?[0-9]+', result)
            if match:
                score = float(match.group())
                return max(0.0, min(1.0, score))
        except Exception:
            pass
        # 回退：检查query中的关键词是否出现在output中
        query_words = set(re.findall(r'[一-鿿]{2,}', query))
        output_words = set(re.findall(r'[一-鿿]{2,}', output))
        overlap = query_words & output_words
        if query_words:
            return min(1.0, len(overlap) / len(query_words) + 0.3)
        return 0.5

    def _score_completeness(self, output: str, expected_keywords: List[str],
                             expected_entities: List[str]) -> float:
        """信息完整度评分（期望关键词/实体覆盖率）"""
        all_expected = set(expected_keywords + expected_entities)
        if not all_expected:
            # 无期望关键词时基于长度启发式
            if len(output) > 500:
                return 0.9
            elif len(output) > 200:
                return 0.7
            elif len(output) > 50:
                return 0.5
            return 0.3
        covered = sum(1 for kw in all_expected if kw.lower() in output.lower())
        return covered / len(all_expected)

    # ========== 批量评价流水线 ==========

    async def run_batch_evaluation(self, test_set: List[TestCase] = None) -> Dict[str, Any]:
        """
        运行批量评价流水线

        Args:
            test_set: 测试用例列表，为空时使用默认测试集

        Returns:
            {total, passed, failed, pass_rate, avg_scores, results, timestamp}
        """
        from agents.agent_coordinator import get_master_agent

        cases = test_set or self._test_set
        master = get_master_agent()
        results: List[BatchResult] = []

        for tc in cases:
            br = BatchResult(test_case_id=tc.id)
            try:
                # 执行查询
                agent_result = await master.process(
                    tc.query,
                    industry=tc.industry,
                )
                br.actual_output = str(agent_result.get("answer", ""))

                # 评分
                br.dimensions = await self.evaluate_single(
                    query=tc.query,
                    agent_output=br.actual_output,
                    intent=tc.intent,
                    expected_keywords=tc.expected_keywords,
                    expected_entities=tc.expected_entities,
                )
                br.passed = br.dimensions.overall_score >= 3.0

            except Exception as e:
                br.error = str(e)
                br.passed = False
                logger.warning(f"测试用例 {tc.id} 执行失败: {e}")

            results.append(br)

        # 汇总统计
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = passed / total if total > 0 else 0

        # 计算各维度平均分
        avg_dims = EvaluationDimensions()
        if results:
            for dim_name in ["intent_accuracy", "task_completion", "fact_accuracy",
                             "structure_quality", "relevance", "completeness", "overall_score"]:
                vals = [getattr(r.dimensions, dim_name, 0) for r in results if r.dimensions]
                setattr(avg_dims, dim_name, sum(vals) / len(vals) if vals else 0)

        # 持久化批量评价结果
        db = self._get_db()
        try:
            for r in results:
                if r.actual_output:
                    db.create_evaluation(
                        message_id=0,
                        user_id=0,
                        auto_score=r.dimensions.overall_score,
                        intent_accuracy=r.dimensions.intent_accuracy,
                        task_completion=r.dimensions.task_completion,
                        response_quality=r.dimensions.relevance,
                    )
        except Exception as e:
            logger.warning(f"批量评价结果持久化失败: {e}")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 3),
            "avg_scores": avg_dims.to_dict(),
            "results": [r.to_dict() for r in results],
            "timestamp": datetime.now().isoformat(),
        }

    async def run_regression_check(self, baseline_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        回归检测 - 对比当前得分与基线得分

        Args:
            baseline_scores: 基线各维度得分

        Returns:
            {is_regression, dimension_diffs, summary}
        """
        current = await self.run_batch_evaluation()
        current_avg = current.get("avg_scores", {})

        diffs = {}
        is_regression = False
        for dim_name, baseline_val in baseline_scores.items():
            current_val = current_avg.get(dim_name, 0)
            diff = current_val - baseline_val
            diffs[dim_name] = round(diff, 3)
            if diff < -0.1:  # 下降超过0.1视为回归
                is_regression = True

        return {
            "is_regression": is_regression,
            "dimension_diffs": diffs,
            "current_scores": current_avg,
            "baseline_scores": baseline_scores,
            "summary": f"{'检测到回归' if is_regression else '无回归'}，平均分变化: {diffs.get('overall_score', 0):+.3f}",
        }


# 单例
_evaluation_service: Any = None


def get_evaluation_service() -> EvaluationService:
    """获取评价服务单例"""
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service
