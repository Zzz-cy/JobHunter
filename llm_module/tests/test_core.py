"""
测试用例
"""
import pytest
import asyncio
from llm_module.core.extractor import KnowledgeExtractor
from llm_module.core.qa_engine import QAEngine
from llm_module.core.kg_builder import KnowledgeGraphBuilder
from llm_module.models.schemas import Entity, Relation, EntityType, RelationType


@pytest.fixture
def extractor():
    return KnowledgeExtractor()


@pytest.fixture
def qa_engine():
    return QAEngine()


@pytest.fixture
def kg_builder():
    return KnowledgeGraphBuilder()


class TestKnowledgeExtractor:
    """测试知识抽取"""

    @pytest.mark.asyncio
    async def test_extract_skills_from_text(self, extractor):
        """测试技能抽取"""
        text = "我们需要招聘一位熟悉Python、Django、MySQL的后端工程师"
        skills = await extractor.extract_skills_from_text(text)
        assert isinstance(skills, list)
        # 注意：这个测试需要配置API Key才能通过

    @pytest.mark.asyncio
    async def test_extract_from_jd(self, extractor):
        """测试JD抽取"""
        jd = """
        高级Python开发工程师
        岗位职责：
        1. 负责后端系统设计与开发
        2. 使用Python、Django、FastAPI等框架
        3. 熟悉MySQL、Redis、MongoDB
        要求：
        1. 3年以上Python开发经验
        2. 熟悉微服务架构
        """
        result = await extractor.extract_from_jd(jd)
        assert result is not None


class TestQAEngine:
    """测试问答引擎"""

    @pytest.mark.asyncio
    async def test_answer(self, qa_engine):
        """测试问答"""
        result = await qa_engine.answer(
            question="Python后端工程师需要什么技能？",
            context="Python后端工程师需要掌握Python语言、Web框架（Django/Flask/FastAPI）、数据库（MySQL/PostgreSQL）等",
        )
        assert result.answer is not None
        assert len(result.answer) > 0


class TestKnowledgeGraph:
    """测试知识图谱"""

    def test_add_entity(self, kg_builder):
        """测试添加实体"""
        entity = Entity(name="Python开发工程师", type=EntityType.JOB)
        kg_builder.add_entities([entity])
        assert len(kg_builder.entities) == 1

    def test_add_relation(self, kg_builder):
        """测试添加关系"""
        entity1 = Entity(name="Python开发工程师", type=EntityType.JOB)
        entity2 = Entity(name="Python", type=EntityType.SKILL)
        kg_builder.add_entities([entity1, entity2])

        relation = Relation(
            source="Python开发工程师",
            target="Python",
            type=RelationType.REQUIRES,
        )
        kg_builder.add_relations([relation])
        assert len(kg_builder.relations) == 1

    def test_query_entities(self, kg_builder):
        """测试查询实体"""
        entity = Entity(name="Java开发工程师", type=EntityType.JOB)
        kg_builder.add_entities([entity])

        results = kg_builder.query_entities(entity_type="job")
        assert len(results) == 1
        assert results[0].name == "Java开发工程师"

    def test_export_import(self, kg_builder):
        """测试导出导入"""
        entity = Entity(name="测试岗位", type=EntityType.JOB)
        kg_builder.add_entities([entity])

        data = kg_builder.export_to_json()
        assert "entities" in data
        assert len(data["entities"]) == 1

        new_builder = KnowledgeGraphBuilder()
        new_builder.import_from_json(data)
        assert len(new_builder.entities) == 1
