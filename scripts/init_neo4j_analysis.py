import json
import os
import re
from collections import Counter, defaultdict
from itertools import combinations
from getpass import getpass

from neo4j import GraphDatabase


# ==================================================
# 1. 找到岗位JSON
# ==================================================
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
JSON_FILE = ROOT_DIR / "db" / "neo4j" / "jobs.json"

print("找到数据文件：", JSON_FILE)


# ==================================================
# 2. Neo4j配置
# ==================================================

# 容器/服务器部署时由环境变量指定; 本地开发默认 localhost
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = "neo4j"

# 优先环境变量(后台/一键同步时由 service 注入, 无终端也不会卡住);
# 手动跑脚本且没配环境变量时才交互输入
password = os.getenv("NEO4J_PASSWORD") or getpass("请输入Neo4j密码：")


# ==================================================
# 3. 岗位方向分类
# 一个岗位可以属于多个方向
# ==================================================

DIRECTION_PATTERNS = {

    "数据分析": [
        r"数据分析",
        r"data analyst",
        r"data analytics",
        r"\bbi\b"
    ],

    "数据挖掘": [
        r"数据挖掘"
    ],

    "大数据": [
        r"大数据",
        r"数据开发",
        r"hadoop",
        r"spark",
        r"flink"
    ],

    "Python开发": [
        r"python"
    ],

    "Java开发": [
        r"java"
    ],

    "C++开发": [
        r"c\+\+"
    ],

    "Go开发": [
        r"golang",
        r"go开发",
        r"go工程师"
    ],

    "前端开发": [
        r"前端",
        r"frontend",
        r"front-end"
    ],

    "后端开发": [
        r"后端",
        r"后台开发",
        r"服务端",
        r"backend"
    ],

    "测试": [
        r"测试",
        r"\bqa\b",
        r"test engineer"
    ],

    "算法/AI": [
        r"算法",
        r"人工智能",
        r"机器学习",
        r"深度学习",
        r"自然语言处理",
        r"\bnlp\b",
        r"计算机视觉",
        r"机器视觉"
    ],

    "运维/云计算": [
        r"运维",
        r"devops",
        r"\bsre\b",
        r"云计算",
        r"云平台",
        r"公有云"
    ],

    "BI/商业智能": [
        r"\bbi\b",
        r"商业智能"
    ],

    "数据库": [
        r"数据库",
        r"\bdba\b"
    ],

    "项目管理": [
        r"项目管理",
        r"项目经理"
    ],

    "产品": [
        r"产品经理",
        r"产品运营"
    ],

    "销售/售前": [
        r"销售",
        r"售前"
    ],

    "风控": [
        r"风控",
        r"风险策略",
        r"反欺诈"
    ],

    "架构": [
        r"架构师",
        r"架构专家"
    ],

    "嵌入式": [
        r"嵌入式"
    ],

    "安全": [
        r"网络安全",
        r"信息安全",
        r"安全工程师"
    ],

    "移动开发": [
        r"android",
        r"\bios\b",
        r"flutter",
        r"移动开发",
        r"移动app"
    ],

    "爬虫": [
        r"爬虫"
    ],

    "音视频": [
        r"音视频"
    ]
}


# ==================================================
# 4. 从岗位名称识别岗位方向
# ==================================================

def get_directions(title):

    title = str(title or "").lower()

    result = set()

    for direction, patterns in DIRECTION_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                title,
                flags=re.IGNORECASE
            ):
                result.add(direction)
                break

    return sorted(result)


# ==================================================
# 5. 获取福利
# ==================================================

def get_benefits(job):

    highlights = job.get("highlights")

    if highlights:

        try:

            if isinstance(highlights, str):
                values = json.loads(highlights)
            else:
                values = highlights

            if isinstance(values, list):

                return [
                    str(x).strip()
                    for x in values
                    if x
                    and str(x).strip()
                    and str(x).strip() != "None"
                ]

        except Exception:
            pass

    advantage = job.get("advantage")

    if not advantage:
        return []

    text = str(advantage).replace("|", "，")

    return [
        x.strip()
        for x in text.split("，")
        if x.strip()
        and x.strip() != "None"
    ]


# ==================================================
# 6. 计算月薪中位值
# ==================================================

def get_salary_mid(job):

    try:
        salary_min = float(
            job.get("salary_min") or 0
        )

        salary_max = float(
            job.get("salary_max") or 0
        )

    except Exception:
        return None

    if salary_min <= 0 and salary_max <= 0:
        return None

    if salary_min > 0 and salary_max > 0:
        return (salary_min + salary_max) / 2

    if salary_min > 0:
        return salary_min

    return salary_max


# ==================================================
# 7. 薪资区间
# ==================================================

def salary_band(salary):

    if salary is None:
        return None

    # salary单位为元/月
    k = salary / 1000

    if k < 10:
        return "10K以下"

    elif k < 20:
        return "10K-20K"

    elif k < 30:
        return "20K-30K"

    elif k < 50:
        return "30K-50K"

    else:
        return "50K以上"


# ==================================================
# 8. 读取数据
# ==================================================

with open(
    JSON_FILE,
    "r",
    encoding="utf-8"
) as f:

    jobs = json.load(f)


print("岗位总数量：", len(jobs))


# ==================================================
# 9. 开始统计
# ==================================================

direction_jobs = Counter()

direction_city = defaultdict(Counter)

direction_education = defaultdict(Counter)

direction_experience = defaultdict(Counter)

direction_benefit = defaultdict(Counter)

direction_salary_band = defaultdict(Counter)

direction_salary_values = defaultdict(list)

direction_quality = defaultdict(list)

job_direction_rows = []

direction_pair = Counter()


for job in jobs:

    job_code = str(
        job.get("job_code") or ""
    ).strip()

    if not job_code:
        continue

    title = job.get("title")

    directions = get_directions(title)

    if not directions:
        continue


    # ----------------------------
    # 一个岗位可能属于多个方向
    # ----------------------------

    for direction in directions:

        direction_jobs[direction] += 1

        job_direction_rows.append({
            "job_code": job_code,
            "direction": direction
        })


        city = str(
            job.get("city") or ""
        ).strip()

        if city:
            direction_city[direction][city] += 1


        education = str(
            job.get("education_req") or ""
        ).strip()

        if education:
            direction_education[direction][education] += 1


        experience = str(
            job.get("experience_req") or ""
        ).strip()

        if experience:
            direction_experience[direction][experience] += 1


        for benefit in get_benefits(job):

            direction_benefit[direction][benefit] += 1


        salary = get_salary_mid(job)

        if salary is not None:

            direction_salary_values[
                direction
            ].append(salary)

            band = salary_band(salary)

            if band:
                direction_salary_band[
                    direction
                ][band] += 1


        try:

            quality = float(
                job.get("quality_score")
            )

            direction_quality[
                direction
            ].append(quality)

        except Exception:
            pass


    # ----------------------------
    # 岗位方向共现，用于相似方向
    # ----------------------------

    if len(directions) >= 2:

        for a, b in combinations(
            sorted(directions),
            2
        ):

            direction_pair[(a, b)] += 1


print("")
print("识别岗位方向数量：", len(direction_jobs))

print("")
print("各岗位方向数量：")

for direction, count in direction_jobs.most_common():

    print(
        direction,
        count
    )


# ==================================================
# 10. 连接Neo4j
# ==================================================

driver = GraphDatabase.driver(
    URI,
    auth=(USER, password)
)

driver.verify_connectivity()

print("")
print("Neo4j连接成功！")


# ==================================================
# 11. 删除以前生成的分析层
# 不删除Job、City、Education等基础数据
# ==================================================

with driver.session(
    database="neo4j"
) as session:

    session.run(
        """
        MATCH (d:JobDirection)
        DETACH DELETE d
        """
    ).consume()

    session.run(
        """
        MATCH (s:SalaryBand)
        DETACH DELETE s
        """
    ).consume()


# ==================================================
# 12. 建立约束
# ==================================================

with driver.session(
    database="neo4j"
) as session:

    session.run(
        """
        CREATE CONSTRAINT job_direction_unique
        IF NOT EXISTS
        FOR (d:JobDirection)
        REQUIRE d.name IS UNIQUE
        """
    ).consume()

    session.run(
        """
        CREATE CONSTRAINT salary_band_unique
        IF NOT EXISTS
        FOR (s:SalaryBand)
        REQUIRE s.name IS UNIQUE
        """
    ).consume()


# ==================================================
# 13. 创建岗位方向节点
# ==================================================

direction_query = """
MERGE (d:JobDirection {name: $name})

SET
    d.total_jobs = $total_jobs,
    d.salary_avg_k = $salary_avg_k,
    d.salary_min_k = $salary_min_k,
    d.salary_max_k = $salary_max_k,
    d.avg_quality = $avg_quality
"""


with driver.session(
    database="neo4j"
) as session:

    for direction, total in direction_jobs.items():

        salaries = direction_salary_values[
            direction
        ]

        qualities = direction_quality[
            direction
        ]


        if salaries:

            salary_avg = round(
                sum(salaries)
                / len(salaries)
                / 1000,
                2
            )

            salary_min = round(
                min(salaries) / 1000,
                2
            )

            salary_max = round(
                max(salaries) / 1000,
                2
            )

        else:

            salary_avg = None
            salary_min = None
            salary_max = None


        if qualities:

            avg_quality = round(
                sum(qualities)
                / len(qualities),
                2
            )

        else:

            avg_quality = None


        session.run(
            direction_query,
            name=direction,
            total_jobs=total,
            salary_avg_k=salary_avg,
            salary_min_k=salary_min,
            salary_max_k=salary_max,
            avg_quality=avg_quality
        ).consume()


# ==================================================
# 14. Job → 岗位方向
# ==================================================

job_direction_query = """
MATCH (j:Job {job_code: $job_code})
MATCH (d:JobDirection {name: $direction})

MERGE (j)-[:IN_DIRECTION]->(d)
"""


with driver.session(
    database="neo4j"
) as session:

    for index, row in enumerate(
        job_direction_rows,
        start=1
    ):

        session.run(
            job_direction_query,
            **row
        ).consume()

        if index % 500 == 0:

            print(
                "岗位方向关系：",
                index,
                "/",
                len(job_direction_rows)
            )


# ==================================================
# 15. 热门城市
# 每个方向只取前5名
# ==================================================

city_query = """
MATCH (d:JobDirection {name: $direction})

MERGE (c:City {name: $city})

MERGE (d)-[r:POPULAR_IN]->(c)

SET
    r.job_count = $job_count,
    r.pct = $pct
"""


with driver.session(
    database="neo4j"
) as session:

    for direction, counter in direction_city.items():

        total = direction_jobs[direction]

        for city, count in counter.most_common(5):

            pct = round(
                count / total * 100,
                2
            )

            session.run(
                city_query,
                direction=direction,
                city=city,
                job_count=count,
                pct=pct
            ).consume()


# ==================================================
# 16. 常见学历
# ==================================================

education_query = """
MATCH (d:JobDirection {name: $direction})

MERGE (e:Education {name: $education})

MERGE (d)-[r:COMMON_EDUCATION]->(e)

SET
    r.job_count = $job_count,
    r.pct = $pct
"""


with driver.session(
    database="neo4j"
) as session:

    for direction, counter in direction_education.items():

        total = direction_jobs[direction]

        for education, count in counter.most_common(3):

            pct = round(
                count / total * 100,
                2
            )

            session.run(
                education_query,
                direction=direction,
                education=education,
                job_count=count,
                pct=pct
            ).consume()


# ==================================================
# 17. 常见经验
# ==================================================

experience_query = """
MATCH (d:JobDirection {name: $direction})

MERGE (e:Experience {name: $experience})

MERGE (d)-[r:COMMON_EXPERIENCE]->(e)

SET
    r.job_count = $job_count,
    r.pct = $pct
"""


with driver.session(
    database="neo4j"
) as session:

    for direction, counter in direction_experience.items():

        total = direction_jobs[direction]

        for experience, count in counter.most_common(4):

            pct = round(
                count / total * 100,
                2
            )

            session.run(
                experience_query,
                direction=direction,
                experience=experience,
                job_count=count,
                pct=pct
            ).consume()


# ==================================================
# 18. 常见福利
# ==================================================

benefit_query = """
MATCH (d:JobDirection {name: $direction})

MERGE (b:Benefit {name: $benefit})

MERGE (d)-[r:COMMON_BENEFIT]->(b)

SET
    r.job_count = $job_count,
    r.pct = $pct
"""


with driver.session(
    database="neo4j"
) as session:

    for direction, counter in direction_benefit.items():

        total = direction_jobs[direction]

        for benefit, count in counter.most_common(5):

            pct = round(
                count / total * 100,
                2
            )

            session.run(
                benefit_query,
                direction=direction,
                benefit=benefit,
                job_count=count,
                pct=pct
            ).consume()


# ==================================================
# 19. 常见薪资区间
# ==================================================

salary_query = """
MATCH (d:JobDirection {name: $direction})

MERGE (s:SalaryBand {name: $salary_band})

MERGE (d)-[r:COMMON_SALARY]->(s)

SET
    r.job_count = $job_count,
    r.pct = $pct
"""


with driver.session(
    database="neo4j"
) as session:

    for direction, counter in direction_salary_band.items():

        total_salary_jobs = sum(
            counter.values()
        )

        if total_salary_jobs == 0:
            continue

        for band, count in counter.most_common(3):

            pct = round(
                count
                / total_salary_jobs
                * 100,
                2
            )

            session.run(
                salary_query,
                direction=direction,
                salary_band=band,
                job_count=count,
                pct=pct
            ).consume()


# ==================================================
# 20. 相似岗位方向
# ==================================================

similar_query = """
MATCH (a:JobDirection {name: $a})
MATCH (b:JobDirection {name: $b})

MERGE (a)-[r:SIMILAR_TO]->(b)

SET
    r.shared_jobs = $shared_jobs,
    r.a_to_b_pct = $a_to_b_pct,
    r.b_to_a_pct = $b_to_a_pct,
    r.jaccard_pct = $jaccard_pct
"""


with driver.session(
    database="neo4j"
) as session:

    for (a, b), shared in direction_pair.items():

        a_total = direction_jobs[a]
        b_total = direction_jobs[b]

        a_to_b = round(
            shared / a_total * 100,
            2
        )

        b_to_a = round(
            shared / b_total * 100,
            2
        )

        union = (
            a_total
            + b_total
            - shared
        )

        jaccard = round(
            shared / union * 100,
            2
        ) if union else 0


        session.run(
            similar_query,
            a=a,
            b=b,
            shared_jobs=shared,
            a_to_b_pct=a_to_b,
            b_to_a_pct=b_to_a,
            jaccard_pct=jaccard
        ).consume()


driver.close()


print("")
print("================================")
print("就业分析知识图谱建立完成！")
print("================================")