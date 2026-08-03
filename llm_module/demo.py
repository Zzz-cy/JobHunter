"""
岗能智绘 - 大模型板块完整演示
多源异构数据驱动岗位能力动态图谱平台
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.extractor import get_extractor
from core.qa_engine import get_qa_engine
from core.kg_builder import get_kg_builder
from services.db_service import get_db_service, JobEntity, SkillEntity, CompetencyRelation
from services.persistence_service import get_persistence_service


async def demo_extract():
    """演示1：从JD抽取岗位能力知识"""
    extractor = get_extractor()

    jd = """
    高级Python后端开发工程师

    岗位职责：
    1. 负责公司核心业务系统的后端设计与开发
    2. 使用Python、Django、FastAPI等框架构建高性能API
    3. 设计并实现微服务架构
    4. 优化数据库查询性能，使用MySQL、Redis、MongoDB
    5. 参与代码评审，保证代码质量

    任职要求：
    1. 计算机相关专业，本科及以上学历
    2. 5年以上Python开发经验
    3. 精通Django、Flask或FastAPI等Web框架
    4. 熟悉MySQL、Redis、消息队列等中间件
    5. 了解Docker、Kubernetes等容器技术
    6. 具备良好的沟通能力和团队协作精神
    """

    print("=" * 60)
    print("【演示1】从JD抽取岗位能力知识")
    print("=" * 60)

    result = await extractor.extract_from_jd(jd)

    print(f"\n抽取到 {len(result.entities)} 个实体:")
    for entity in result.entities:
        print(f"  - {entity.name} ({entity.type.value})")

    print(f"\n抽取到 {len(result.relations)} 个关系:")
    for relation in result.relations:
        print(f"  - {relation.source} --{relation.type.value}--> {relation.target}")

    return result


async def demo_qa():
    """演示2：智能问答"""
    qa = get_qa_engine()

    print("\n" + "=" * 60)
    print("【演示2】智能问答")
    print("=" * 60)

    question = "Python后端工程师需要掌握哪些核心技能？"
    context = """
    Python后端工程师的核心技能包括：
    1. Python语言基础：熟悉Python语法、数据结构、面向对象编程
    2. Web框架：Django、Flask、FastAPI等
    3. 数据库：MySQL、PostgreSQL、Redis、MongoDB
    4. 消息队列：RabbitMQ、Kafka、Celery
    5. 容器技术：Docker、Kubernetes
    6. 版本控制：Git
    """

    print(f"\n问题: {question}")
    result = await qa.answer(question, context)
    print(f"\n回答: {result.answer}")


async def demo_kg():
    """演示3：知识图谱构建与查询"""
    kg = get_kg_builder()

    print("\n" + "=" * 60)
    print("【演示3】知识图谱构建与查询")
    print("=" * 60)

    # 先抽取知识
    result = await demo_extract()

    # 构建知识图谱
    kg.build_from_knowledge(result)

    print(f"\n知识图谱统计:")
    print(f"  - 实体数: {len(kg.entities)}")
    print(f"  - 关系数: {len(kg.relations)}")

    # 查询实体
    print(f"\n查询所有岗位实体:")
    jobs = kg.query_entities(entity_type="job")
    for job in jobs:
        print(f"  - {job.name}")

    # 获取子图
    if jobs:
        print(f"\n'{jobs[0].name}' 的子图:")
        try:
            subgraph = kg.get_subgraph(jobs[0].name, depth=2)
            print(f"  - 相关实体: {len(subgraph['entities'])}")
            print(f"  - 相关关系: {len(subgraph['relations'])}")
        except Exception as e:
            print(f"  获取子图时出错: {e}")

    # 保存到持久化
    print("\n保存知识图谱到持久化存储...")
    kg.save_to_persistence()

    return kg


def demo_database():
    """演示4：数据库存储"""
    print("\n" + "=" * 60)
    print("【演示4】数据库存储")
    print("=" * 60)

    db = get_db_service()

    # 创建岗位
    job = JobEntity(
        name="高级Python后端开发工程师",
        category="技术",
        description="负责核心业务系统的后端设计与开发",
        requirements="5年以上Python经验，精通Django/FastAPI",
        salary_range="25k-40k",
        location="北京",
        source="demo",
    )
    job_id = db.create_job(job)
    print(f"\n创建岗位: {job.name} (ID: {job_id})")

    # 创建技能
    skills = [
        SkillEntity(name="Python", category="编程语言", description="Python编程语言"),
        SkillEntity(name="Django", category="Web框架", description="Python Web框架"),
        SkillEntity(name="FastAPI", category="Web框架", description="现代Python Web框架"),
        SkillEntity(name="MySQL", category="数据库", description="关系型数据库"),
        SkillEntity(name="Redis", category="数据库", description="内存数据库"),
    ]

    for skill in skills:
        skill_id = db.create_skill(skill)
        print(f"创建技能: {skill.name} (ID: {skill_id})")

    # 创建关系
    for skill in skills:
        relation = CompetencyRelation(
            source_type="job",
            source_name=job.name,
            target_type="skill",
            target_name=skill.name,
            relation_type="requires",
            weight=1.0,
        )
        db.create_relation(relation)
        print(f"创建关系: {job.name} --requires--> {skill.name}")

    # 查询
    print("\n查询所有岗位:")
    jobs = db.search_jobs()
    for j in jobs:
        print(f"  - {j['name']} ({j['category']})")

    # 统计
    stats = db.get_stats()
    print(f"\n数据库统计:")
    print(f"  - 岗位数: {stats['jobs']}")
    print(f"  - 技能数: {stats['skills']}")
    print(f"  - 关系数: {stats['relations']}")
    print(f"  - 数据库类型: {stats['database']}")


def demo_persistence():
    """演示5：数据持久化"""
    print("\n" + "=" * 60)
    print("【演示5】数据持久化")
    print("=" * 60)

    persist = get_persistence_service()

    # 导出数据
    export_path = str(Path(__file__).parent / "data" / "export" / "knowledge_graph_export.json")
    Path(export_path).parent.mkdir(parents=True, exist_ok=True)

    success = persist.export_to_json(export_path)
    if success:
        print(f"\n数据已导出到: {export_path}")
    else:
        print("\n导出失败或数据为空")


async def main():
    """主函数"""
    print("=" * 60)
    print("岗能智绘 - 多源异构数据驱动岗位能力动态图谱平台")
    print("=" * 60)
    print("\n技术栈:")
    print("  - 大模型: 智谱GLM-4系列 (GLM-4-Flash/Air/Plus)")
    print("  - 知识抽取: NER + LLM")
    print("  - 数据存储: SQLite/MySQL + JSON持久化")
    print("  - 知识图谱: 内存 + Neo4j(可选)")
    print("  - 搜索引擎: Elasticsearch(可选)")
    print("=" * 60)

    try:
        # 演示知识抽取
        await demo_extract()

        # 演示智能问答
        await demo_qa()

        # 演示知识图谱
        await demo_kg()

        # 演示数据库存储
        demo_database()

        # 演示数据持久化
        demo_persistence()

    except Exception as e:
        print(f"\n演示出错: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
