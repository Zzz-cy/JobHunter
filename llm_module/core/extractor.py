"""
知识抽取模块 - 从多源异构数据中抽取岗位能力知识
"""
import json
from typing import Dict, Any, List
from services.llm_service import get_llm_service
from models.schemas import (
    ExtractedKnowledge, Entity, Relation,
    EntityType, RelationType, JobDescription
)
from models.prompts import JOB_EXTRACTION_PROMPT
from utils.logger import get_logger
logger = get_logger("core.extractor")


class KnowledgeExtractor:
    """知识抽取器 - 从文本中抽取岗位能力知识"""

    def __init__(self):
        self.llm = get_llm_service()

    async def extract_from_jd(self, jd_text: str) -> ExtractedKnowledge:
        """
        从岗位描述(JD)中抽取结构化知识

        Args:
            jd_text: 岗位描述文本

        Returns:
            ExtractedKnowledge: 抽取的知识结构
        """
        logger.info(f"开始从JD抽取知识，文本长度: {len(jd_text)}")

        prompt = JOB_EXTRACTION_PROMPT.format(jd_text=jd_text)
        logger.debug(f"JD抽取: text_length={len(jd_text)}, prompt_length={len(prompt)}")
        result = await self.llm.extract_json(prompt)

        if "error" in result:
            logger.error(f"知识抽取失败: {result['error']}")
            return ExtractedKnowledge(raw_text=jd_text)

        # 解析实体
        entities = []
        for e in result.get("entities", []):
            try:
                entity = Entity(
                    name=e["name"],
                    type=EntityType(e["type"]),
                    properties=e.get("properties", {}),
                )
                entities.append(entity)
            except (KeyError, ValueError) as ex:
                logger.warning(f"实体解析失败: {ex}")

        # 解析关系
        relations = []
        for r in result.get("relations", []):
            try:
                relation = Relation(
                    source=r["source"],
                    target=r["target"],
                    type=RelationType(r["type"]),
                )
                relations.append(relation)
            except (KeyError, ValueError) as ex:
                logger.warning(f"关系解析失败: {ex}")

        logger.info(f"抽取完成: {len(entities)}个实体, {len(relations)}个关系")

        return ExtractedKnowledge(
            entities=entities,
            relations=relations,
            raw_text=jd_text,
        )

    async def extract_from_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        从简历中抽取技能和经验信息

        Args:
            resume_text: 简历文本

        Returns:
            结构化简历信息
        """
        prompt = f"""请从以下简历中抽取关键信息，以JSON格式输出：

【简历内容】
{resume_text}

请输出以下结构：
{{
    "name": "姓名",
    "skills": ["技能1", "技能2"],
    "experience": [
        {{
            "company": "公司名",
            "position": "职位",
            "duration": "时间段",
            "description": "工作描述"
        }}
    ],
    "education": [
        {{
            "school": "学校",
            "degree": "学位",
            "major": "专业"
        }}
    ],
    "certificates": ["证书1", "证书2"],
    "projects": [
        {{
            "name": "项目名称",
            "description": "项目描述",
            "skills_used": ["使用的技能"]
        }}
    ]
}}

只输出JSON，不要其他内容。"""

        return await self.llm.extract_json(prompt)

    async def extract_skills_from_text(self, text: str) -> List[str]:
        """
        从任意文本中抽取技能关键词

        Args:
            text: 输入文本

        Returns:
            技能关键词列表
        """
        prompt = f"""请从以下文本中抽取所有提到的技能、技术、工具、框架等关键词。

【文本】
{text}

请以JSON数组格式输出技能列表：
["技能1", "技能2", "技能3"]

只输出JSON数组，不要其他内容。"""

        result = await self.llm.extract_json(prompt)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "error" not in result:
            # 尝试从各种可能的键中提取
            for key in ["skills", "技能", "result", "data"]:
                if key in result:
                    return result[key]
        return []

    async def analyze_skill_relationship(self, skills: List[str]) -> List[Dict[str, str]]:
        """
        分析技能之间的关系

        Args:
            skills: 技能列表

        Returns:
            技能关系列表
        """
        skills_str = ", ".join(skills)
        prompt = f"""请分析以下技能之间的关系，以JSON格式输出：

【技能列表】
{skills_str}

请分析以下关系类型：
1. prerequisite（前置依赖）：学习A需要先掌握B
2. similar_to（相似）：A和B功能相似或可替代
3. complementary（互补）：A和B经常一起使用

输出格式：
[
    {{"source": "技能A", "target": "技能B", "type": "prerequisite", "reason": "原因说明"}},
    {{"source": "技能C", "target": "技能D", "type": "similar_to", "reason": "原因说明"}}
]

只输出JSON数组，不要其他内容。"""

        result = await self.llm.extract_json(prompt)
        if isinstance(result, list):
            return result
        return []


# 单例
_extractor: Any = None


def get_extractor() -> KnowledgeExtractor:
    """获取知识抽取器单例"""
    global _extractor
    if _extractor is None:
        _extractor = KnowledgeExtractor()
    return _extractor
