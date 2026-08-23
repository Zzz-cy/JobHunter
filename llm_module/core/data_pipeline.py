"""
数据预处理管道 - 处理多源异构数据
"""
import re
import json
from typing import List, Dict, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field

from utils.logger import get_logger
logger = get_logger("core.data_pipeline")


@dataclass
class RawData:
    """原始数据"""
    source: str           # 数据来源
    content: str          # 原始内容
    metadata: Dict[str, Any] = field(default_factory=dict)
    data_type: str = "text"  # text/json/html/pdf


@dataclass
class ProcessedData:
    """处理后的数据"""
    source: str
    content: str          # 清洗后的文本
    metadata: Dict[str, Any]
    entities: List[Dict] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


class DataPreprocessor:
    """数据预处理器"""

    def __init__(self):
        self.pipelines: Dict[str, List[Callable]] = {}

    def _clean_text(self, text: str) -> str:
        """
        清洗文本

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 去除特殊字符
        text = re.sub(r'[^一-龥a-zA-Z0-9\s.,;:!?-]', '', text)
        # 去除多余空格
        text = text.strip()

        return text

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """
        从JD文本中提取各个部分

        Args:
            text: JD文本

        Returns:
            各部分内容的字典
        """
        sections = {
            "title": "",
            "company": "",
            "salary": "",
            "location": "",
            "requirements": "",
            "responsibilities": "",
            "benefits": "",
            "raw": text,
        }

        # 提取岗位名称（通常在开头）
        title_patterns = [
            r'^(.*?)(?:\n|$)',  # 第一行
            r'【(.*?)】',         # 【岗位名称】
            r'职位[：:]\s*(.+?)(?:\n|$)',  # 职位：xxx
        ]

        for pattern in title_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                sections["title"] = match.group(1).strip()
                break

        # 提取薪资信息
        salary_pattern = r'(\d+[kK]?-\d+[kK]?)|(\d+万[以]?[上]?)|(\d+[kK][以]?[上]?)'
        salary_match = re.search(salary_pattern, text)
        if salary_match:
            sections["salary"] = salary_match.group()

        # 提取地点
        location_pattern = r'([一-龥]{2,5}(?:市|区|县))'
        location_match = re.search(location_pattern, text)
        if location_match:
            sections["location"] = location_match.group()

        # 提取任职要求
        req_patterns = [
            r'任职要求[：:]?(.*?)(?:岗位职责|工作职责|工作内容|$)',
            r'岗位要求[：:]?(.*?)(?:岗位职责|工作职责|工作内容|$)',
            r'任职资格[：:]?(.*?)(?:岗位职责|工作职责|工作内容|$)',
        ]
        for pattern in req_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                sections["requirements"] = match.group(1).strip()
                break

        # 提取岗位职责
        resp_patterns = [
            r'岗位职责[：:]?(.*?)(?:任职要求|岗位要求|任职资格|$)',
            r'工作职责[：:]?(.*?)(?:任职要求|岗位要求|任职资格|$)',
            r'工作内容[：:]?(.*?)(?:任职要求|岗位要求|任职资格|$)',
        ]
        for pattern in resp_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                sections["responsibilities"] = match.group(1).strip()
                break

        return sections

    def _extract_skills(self, text: str, industry: str = "") -> List[str]:
        """
        从文本中提取技能关键词

        Args:
            text: 输入文本
            industry: 行业标识 (it/finance/healthcare/manufacturing/education)

        Returns:
            技能关键词列表
        """
        from utils.config import INDUSTRY_SKILL_KEYWORDS, DEFAULT_INDUSTRY

        # 根据行业选择关键词集
        industry_key = industry.lower() if industry else DEFAULT_INDUSTRY
        skill_keywords = INDUSTRY_SKILL_KEYWORDS.get(
            industry_key,
            INDUSTRY_SKILL_KEYWORDS.get(DEFAULT_INDUSTRY, set())
        )

        text_lower = text.lower()
        found_skills = []

        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill)

        return found_skills

    def process_jd(self, raw_data: RawData) -> ProcessedData:
        """
        处理岗位描述(JD)

        Args:
            raw_data: 原始数据

        Returns:
            处理后的数据
        """
        logger.info(f"处理JD数据: {raw_data.source}")

        # 清洗文本
        cleaned_text = self._clean_text(raw_data.content)

        # 提取各部分
        sections = self._extract_sections(cleaned_text)

        # 提取技能
        all_text = f"{sections.get('requirements', '')} {sections.get('responsibilities', '')}"
        industry = raw_data.metadata.get("industry", "")
        skills = self._extract_skills(all_text, industry=industry)
        logger.debug(f"JD预处理: source={raw_data.source}, sections={list(sections.keys())}, skills={skills}")

        # 构建处理后的数据
        processed = ProcessedData(
            source=raw_data.source,
            content=cleaned_text,
            metadata={
                **raw_data.metadata,
                "sections": sections,
                "type": "job_description",
            },
            keywords=skills,
        )

        logger.info(f"JD处理完成: {len(skills)}个技能关键词")
        return processed

    def process_resume(self, raw_data: RawData) -> ProcessedData:
        """
        处理简历

        Args:
            raw_data: 原始数据

        Returns:
            处理后的数据
        """
        logger.info(f"处理简历数据: {raw_data.source}")

        # 清洗文本
        cleaned_text = self._clean_text(raw_data.content)

        # 提取技能
        industry = raw_data.metadata.get("industry", "")
        skills = self._extract_skills(cleaned_text, industry=industry)

        # 构建处理后的数据
        processed = ProcessedData(
            source=raw_data.source,
            content=cleaned_text,
            metadata={
                **raw_data.metadata,
                "type": "resume",
            },
            keywords=skills,
        )

        logger.info(f"简历处理完成: {len(skills)}个技能关键词")
        return processed

    def process_skill_definition(self, raw_data: RawData) -> ProcessedData:
        """
        处理技能定义

        Args:
            raw_data: 原始数据

        Returns:
            处理后的数据
        """
        logger.info(f"处理技能定义: {raw_data.source}")

        # 清洗文本
        cleaned_text = self._clean_text(raw_data.content)

        # 提取技能名称
        industry = raw_data.metadata.get("industry", "")
        skills = self._extract_skills(cleaned_text, industry=industry)

        processed = ProcessedData(
            source=raw_data.source,
            content=cleaned_text,
            metadata={
                **raw_data.metadata,
                "type": "skill_definition",
            },
            keywords=skills,
        )

        return processed

    def process_batch(
        self,
        raw_data_list: List[RawData],
        data_type: str = "auto",
    ) -> List[ProcessedData]:
        """
        批量处理数据

        Args:
            raw_data_list: 原始数据列表
            data_type: 数据类型 (auto/jd/resume/skill)

        Returns:
            处理后的数据列表
        """
        results = []

        for raw_data in raw_data_list:
            try:
                # 自动判断类型
                if data_type == "auto":
                    if "jd" in raw_data.source.lower() or "job" in raw_data.source.lower():
                        data_type = "jd"
                    elif "resume" in raw_data.source.lower() or "cv" in raw_data.source.lower():
                        data_type = "resume"
                    else:
                        data_type = "skill"

                # 根据类型选择处理方式
                if data_type == "jd":
                    processed = self.process_jd(raw_data)
                elif data_type == "resume":
                    processed = self.process_resume(raw_data)
                else:
                    processed = self.process_skill_definition(raw_data)

                results.append(processed)

            except Exception as e:
                logger.error(f"处理数据失败 [{raw_data.source}]: {e}")
                continue

        logger.info(f"批量处理完成: {len(results)}/{len(raw_data_list)}")
        return results

    def export_to_json(self, data: ProcessedData, output_path: str):
        """
        导出处理后的数据为JSON

        Args:
            data: 处理后的数据
            output_path: 输出路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "source": data.source,
                "content": data.content,
                "metadata": data.metadata,
                "keywords": data.keywords,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"数据已导出: {output_path}")


# 单例
_preprocessor: Any = None


def get_preprocessor() -> DataPreprocessor:
    """获取预处理器单例"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = DataPreprocessor()
    return _preprocessor
