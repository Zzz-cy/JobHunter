import json
from neo4j import GraphDatabase
from getpass import getpass


# ==============================
# 1. 配置
# ==============================
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
JSON_FILE = ROOT_DIR / "db" / "neo4j" / "jobs.json"


# 第一次只导入50条测试
LIMIT = None

uri = "bolt://localhost:7687"
user = "neo4j"

password = getpass("请输入Neo4j密码：")


# ==============================
# 2. 读取JSON
# ==============================

with open(JSON_FILE, "r", encoding="utf-8") as f:
    jobs = json.load(f)

print(f"JSON总岗位数量：{len(jobs)}")

if LIMIT:
    jobs = jobs[:LIMIT]

print(f"本次准备导入：{len(jobs)} 条岗位")


# ==============================
# 3. 处理福利字段
# ==============================

def get_benefits(job):
    highlights = job.get("highlights")

    if highlights:
        try:
            if isinstance(highlights, str):
                result = json.loads(highlights)
            else:
                result = highlights

            if isinstance(result, list):
                return [
                    str(x).strip()
                    for x in result
                    if x and str(x).strip() not in ("None", "null")
                ]

        except Exception:
            pass

    advantage = job.get("advantage")

    if not advantage:
        return []

    text = str(advantage)

    text = text.replace("|", "，")

    return [
        x.strip()
        for x in text.split("，")
        if x.strip() and x.strip() != "None"
    ]


# ==============================
# 4. Neo4j连接
# ==============================

driver = GraphDatabase.driver(
    uri,
    auth=(user, password)
)

driver.verify_connectivity()

print("Neo4j连接成功，开始导入……")


# ==============================
# 5. 创建约束
# ==============================

constraints = [
    """
    CREATE CONSTRAINT job_code_unique IF NOT EXISTS
    FOR (j:Job)
    REQUIRE j.job_code IS UNIQUE
    """,

    """
    CREATE CONSTRAINT city_name_unique IF NOT EXISTS
    FOR (c:City)
    REQUIRE c.name IS UNIQUE
    """,

    """
    CREATE CONSTRAINT education_name_unique IF NOT EXISTS
    FOR (e:Education)
    REQUIRE e.name IS UNIQUE
    """,

    """
    CREATE CONSTRAINT experience_name_unique IF NOT EXISTS
    FOR (e:Experience)
    REQUIRE e.name IS UNIQUE
    """,

    """
    CREATE CONSTRAINT source_name_unique IF NOT EXISTS
    FOR (s:Source)
    REQUIRE s.name IS UNIQUE
    """,

    """
    CREATE CONSTRAINT benefit_name_unique IF NOT EXISTS
    FOR (b:Benefit)
    REQUIRE b.name IS UNIQUE
    """
]

with driver.session(database="neo4j") as session:
    for query in constraints:
        session.run(query).consume()


# ==============================
# 6. 导入岗位
# ==============================

job_query = """
MERGE (j:Job {job_code: $job_code})

SET
    j.id = $id,
    j.title = $title,
    j.company_id = $company_id,
    j.salary_min = $salary_min,
    j.salary_max = $salary_max,
    j.salary_unit = $salary_unit,
    j.salary_months = $salary_months,
    j.job_type = $job_type,
    j.status = $status,
    j.publish_at = $publish_at,
    j.quality_score = $quality_score,
    j.source_url = $source_url
"""


city_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (c:City {name: $city})

MERGE (j)-[:LOCATED_IN]->(c)
"""


district_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (d:District {
    name: $district,
    city: $city
})

MERGE (j)-[:LOCATED_IN_DISTRICT]->(d)

WITH j, d

MATCH (c:City {name: $city})

MERGE (d)-[:BELONGS_TO]->(c)
"""


education_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (e:Education {name: $education})

MERGE (j)-[:REQUIRES_EDUCATION]->(e)
"""


experience_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (e:Experience {name: $experience})

MERGE (j)-[:REQUIRES_EXPERIENCE]->(e)
"""


source_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (s:Source {name: $source})

MERGE (j)-[:FROM_SOURCE]->(s)
"""


company_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (c:Company {company_id: $company_id})

MERGE (j)-[:POSTED_BY]->(c)
"""


benefit_query = """
MATCH (j:Job {job_code: $job_code})

MERGE (b:Benefit {name: $benefit})

MERGE (j)-[:OFFERS_BENEFIT]->(b)
"""


# ==============================
# 7. 正式执行
# ==============================

with driver.session(database="neo4j") as session:

    for index, job in enumerate(jobs, start=1):

        job_code = str(job.get("job_code", "")).strip()

        if not job_code:
            continue

        session.run(
            job_query,
            job_code=job_code,
            id=job.get("id"),
            title=job.get("title"),
            company_id=job.get("company_id"),
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_unit=job.get("salary_unit"),
            salary_months=job.get("salary_months"),
            job_type=job.get("job_type"),
            status=job.get("status"),
            publish_at=job.get("publish_at"),
            quality_score=job.get("quality_score"),
            source_url=job.get("source_url")
        ).consume()


        city = job.get("city")

        if city:
            session.run(
                city_query,
                job_code=job_code,
                city=str(city).strip()
            ).consume()


        district = job.get("district")

        if district and city:
            session.run(
                district_query,
                job_code=job_code,
                district=str(district).strip(),
                city=str(city).strip()
            ).consume()


        education = job.get("education_req")

        if education:
            session.run(
                education_query,
                job_code=job_code,
                education=str(education).strip()
            ).consume()


        experience = job.get("experience_req")

        if experience:
            session.run(
                experience_query,
                job_code=job_code,
                experience=str(experience).strip()
            ).consume()


        source = job.get("source")

        if source:
            session.run(
                source_query,
                job_code=job_code,
                source=str(source).strip()
            ).consume()


        company_id = job.get("company_id")

        if company_id is not None:
            session.run(
                company_query,
                job_code=job_code,
                company_id=company_id
            ).consume()


        benefits = get_benefits(job)

        for benefit in benefits:
            session.run(
                benefit_query,
                job_code=job_code,
                benefit=benefit
            ).consume()


        print(
            f"[{index}/{len(jobs)}] "
            f"已导入：{job.get('title')}"
        )


driver.close()

print("")
print("============================")
print("知识图谱导入完成！")
print("============================")