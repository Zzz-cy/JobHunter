"""
A/B测试框架 - 实验配置、流量分配、指标对比、统计显著性
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from utils.logger import get_logger
logger = get_logger("services.ab_test_service")


@dataclass
class Experiment:
    """A/B实验配置"""
    id: str = ""
    name: str = ""
    description: str = ""
    # 实验组配置
    control: Dict[str, Any] = field(default_factory=dict)  # 对照组
    treatment: Dict[str, Any] = field(default_factory=dict)  # 实验组
    # 流量分配比例（treatment组占比，0-1）
    traffic_split: float = 0.5
    # 状态
    status: str = "draft"  # draft / running / completed / stopped
    # 统计
    control_samples: int = 0
    treatment_samples: int = 0
    control_scores: List[float] = field(default_factory=list)
    treatment_scores: List[float] = field(default_factory=list)
    # 结果
    result: Optional[Dict[str, Any]] = None
    # 时间
    created_at: str = ""
    started_at: str = ""
    stopped_at: str = ""


class ABTestService:
    """A/B测试服务"""

    def __init__(self):
        self._db = None
        self._experiments: Dict[str, Experiment] = {}

    def _get_db(self):
        if self._db is None:
            from services.db_service import get_db_service
            self._db = get_db_service()
        return self._db

    # ========== 实验管理 ==========

    def create_experiment(self, name: str, description: str,
                          control: Dict[str, Any], treatment: Dict[str, Any],
                          traffic_split: float = 0.5) -> Experiment:
        """
        创建A/B实验

        Args:
            name: 实验名称
            description: 实验描述
            control: 对照组配置（如 {prompt: "...", model: "glm-4-air"}）
            treatment: 实验组配置
            traffic_split: 实验组流量占比（0-1）

        Returns:
            Experiment对象
        """
        exp_id = f"exp_{hashlib.md5(f'{name}:{time.time()}'.encode()).hexdigest()[:8]}"
        exp = Experiment(
            id=exp_id,
            name=name,
            description=description,
            control=control,
            treatment=treatment,
            traffic_split=max(0.1, min(0.9, traffic_split)),
            status="draft",
            created_at=datetime.now().isoformat(),
        )
        self._experiments[exp_id] = exp
        logger.info(f"A/B实验已创建: {exp_id} - {name}")
        return exp

    def start_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """启动实验"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        if exp.status != "draft":
            logger.warning(f"实验 {experiment_id} 状态为 {exp.status}，无法启动")
            return None
        exp.status = "running"
        exp.started_at = datetime.now().isoformat()
        logger.info(f"A/B实验已启动: {experiment_id}")
        return exp

    def stop_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """停止实验"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        exp.status = "stopped"
        exp.stopped_at = datetime.now().isoformat()
        # 自动分析结果
        exp.result = self.analyze_experiment(experiment_id)
        logger.info(f"A/B实验已停止: {experiment_id}")
        return exp

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """获取实验"""
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> List[Dict[str, Any]]:
        """列出所有实验"""
        return [
            {
                "id": exp.id,
                "name": exp.name,
                "status": exp.status,
                "traffic_split": exp.traffic_split,
                "control_samples": exp.control_samples,
                "treatment_samples": exp.treatment_samples,
                "created_at": exp.created_at,
                "started_at": exp.started_at,
            }
            for exp in self._experiments.values()
        ]

    # ========== 流量分配 ==========

    def assign_variant(self, experiment_id: str, user_id: int = 0,
                       session_id: str = "") -> str:
        """
        为用户/会话分配实验变体

        Args:
            experiment_id: 实验ID
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            "control" 或 "treatment"
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != "running":
            return "control"  # 非运行状态默认返回对照组

        # 基于用户ID或会话ID的确定性分配（同一用户始终分到同一组）
        key = f"{experiment_id}:{user_id or session_id}"
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100
        if hash_val < exp.traffic_split * 100:
            return "treatment"
        return "control"

    # ========== 指标记录 ==========

    def record_score(self, experiment_id: str, variant: str, score: float) -> None:
        """
        记录评价得分

        Args:
            experiment_id: 实验ID
            variant: "control" 或 "treatment"
            score: 评价得分（0-5）
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != "running":
            return

        if variant == "control":
            exp.control_scores.append(score)
            exp.control_samples += 1
        elif variant == "treatment":
            exp.treatment_scores.append(score)
            exp.treatment_samples += 1

    # ========== 统计分析 ==========

    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        分析实验结果

        Returns:
            {control_mean, treatment_mean, p_value, is_significant,
             confidence_interval, winner, recommendation}
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "实验不存在"}

        control_scores = exp.control_scores
        treatment_scores = exp.treatment_scores

        if not control_scores or not treatment_scores:
            return {
                "error": "样本不足",
                "control_samples": len(control_scores),
                "treatment_samples": len(treatment_scores),
            }

        # 计算均值
        control_mean = sum(control_scores) / len(control_scores)
        treatment_mean = sum(treatment_scores) / len(treatment_scores)

        # 计算标准差
        control_std = self._std(control_scores)
        treatment_std = self._std(treatment_scores)

        # 计算p值（Welch's t-test近似）
        p_value = self._welch_ttest(control_scores, treatment_scores)

        # 置信区间
        ci = self._confidence_interval(treatment_mean - control_mean,
                                        control_std, treatment_std,
                                        len(control_scores), len(treatment_scores))

        # 判断显著性（p < 0.05）
        is_significant = p_value < 0.05

        # 判定胜出者
        winner = None
        recommendation = ""
        if is_significant:
            if treatment_mean > control_mean:
                winner = "treatment"
                recommendation = f"实验组显著优于对照组（均值{treatment_mean:.2f} vs {control_mean:.2f}，p={p_value:.4f}），建议推广实验组配置"
            else:
                winner = "control"
                recommendation = f"对照组显著优于实验组（均值{control_mean:.2f} vs {treatment_mean:.2f}，p={p_value:.4f}），建议保持对照组配置"
        else:
            recommendation = f"两组无显著差异（p={p_value:.4f}），建议延长实验或增加样本量"

        return {
            "control_mean": round(control_mean, 3),
            "control_std": round(control_std, 3),
            "control_samples": len(control_scores),
            "treatment_mean": round(treatment_mean, 3),
            "treatment_std": round(treatment_std, 3),
            "treatment_samples": len(treatment_scores),
            "mean_diff": round(treatment_mean - control_mean, 3),
            "p_value": round(p_value, 4),
            "is_significant": is_significant,
            "confidence_interval_95": ci,
            "winner": winner,
            "recommendation": recommendation,
        }

    def _std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _welch_ttest(self, a: List[float], b: List[float]) -> float:
        """Welch's t-test 返回近似p值"""
        n1, n2 = len(a), len(b)
        if n1 < 2 or n2 < 2:
            return 1.0

        mean1, mean2 = sum(a) / n1, sum(b) / n2
        var1 = sum((x - mean1) ** 2 for x in a) / (n1 - 1)
        var2 = sum((x - mean2) ** 2 for x in b) / (n2 - 1)

        se = math.sqrt(var1 / n1 + var2 / n2)
        if se == 0:
            return 1.0

        t_stat = (mean1 - mean2) / se

        # 自由度（Welch-Satterthwaite方程）
        df_num = (var1 / n1 + var2 / n2) ** 2
        df_den = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
        if df_den == 0:
            return 1.0
        df = df_num / df_den

        # 近似p值（使用正态分布近似，对于df > 30足够精确）
        p_value = 2 * (1 - self._normal_cdf(abs(t_stat)))
        return p_value

    def _normal_cdf(self, x: float) -> float:
        """标准正态分布CDF近似"""
        # 使用误差函数近似
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _confidence_interval(self, mean_diff: float, std1: float, std2: float,
                             n1: int, n2: int, confidence: float = 0.95) -> List[float]:
        """计算置信区间"""
        se = math.sqrt(std1 ** 2 / max(n1, 1) + std2 ** 2 / max(n2, 1))
        # 使用z=1.96作为95%置信区间
        z = 1.96
        return [round(mean_diff - z * se, 3), round(mean_diff + z * se, 3)]

    # ========== 自动推广 ==========

    def auto_promote(self, experiment_id: str) -> Dict[str, Any]:
        """
        如果实验组显著优于对照组，自动切换为默认配置

        Returns:
            {promoted: bool, config: dict, reason: str}
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"promoted": False, "config": {}, "reason": "实验不存在"}

        if not exp.result:
            exp.result = self.analyze_experiment(experiment_id)

        result = exp.result
        if result.get("error"):
            return {"promoted": False, "config": {}, "reason": f"分析失败: {result['error']}"}

        if not result.get("is_significant"):
            return {"promoted": False, "config": exp.control,
                    "reason": f"无显著差异(p={result.get('p_value', 1):.4f})，保持对照组"}

        if result.get("winner") == "treatment":
            # 自动推广实验组配置
            exp.status = "completed"
            exp.stopped_at = datetime.now().isoformat()
            logger.info(f"实验组自动推广: {experiment_id}, 配置: {exp.treatment}")
            return {
                "promoted": True,
                "config": exp.treatment,
                "reason": result.get("recommendation", "实验组胜出"),
            }
        else:
            return {
                "promoted": False,
                "config": exp.control,
                "reason": result.get("recommendation", "对照组胜出"),
            }


# 单例
_ab_test_service: Any = None


def get_ab_test_service() -> ABTestService:
    """获取A/B测试服务单例"""
    global _ab_test_service
    if _ab_test_service is None:
        _ab_test_service = ABTestService()
    return _ab_test_service
