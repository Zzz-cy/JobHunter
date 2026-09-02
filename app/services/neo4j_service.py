from neo4j import GraphDatabase

from app.core.config import settings


class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(
                settings.NEO4J_USER,
                settings.NEO4J_PASSWORD,
            ),
        )

    def close(self):
        self.driver.close()

    def health(self):
        records, _, _ = self.driver.execute_query(
            "RETURN 1 AS test",
            database_="neo4j",
        )

        return records[0]["test"] == 1

    def get_directions(self):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (d:JobDirection)

            RETURN
                d.name AS name,
                d.total_jobs AS total_jobs,
                d.salary_avg_k AS salary_avg_k

            ORDER BY d.total_jobs DESC
            """,
            database_="neo4j",
        )

        return [record.data() for record in records]

    def get_direction_value(self, keyword: str):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (d:JobDirection {name: $keyword})

            OPTIONAL MATCH (d)-[r]-(n)

            WHERE type(r) IN [
                "POPULAR_IN",
                "COMMON_EDUCATION",
                "COMMON_EXPERIENCE",
                "COMMON_SALARY",
                "COMMON_BENEFIT",
                "SIMILAR_TO",
                "DEMANDS"
            ]

            RETURN
                d.name AS center_name,
                d.total_jobs AS total_jobs,
                d.salary_avg_k AS salary_avg_k,
                d.salary_min_k AS salary_min_k,
                d.salary_max_k AS salary_max_k,

                type(r) AS relation_type,
                properties(r) AS relation_properties,

                labels(n) AS node_labels,
                n.name AS node_name
            """,
            keyword=keyword,
            database_="neo4j",
        )

        if not records:
            return None

        first = records[0]

        center = {
            "id": f"JobDirection:{first['center_name']}",
            "name": first["center_name"],
            "type": "JobDirection",
            "total_jobs": first["total_jobs"],
            "salary_avg_k": first["salary_avg_k"],
            "salary_min_k": first["salary_min_k"],
            "salary_max_k": first["salary_max_k"],
        }

        groups = {
            "skills": [],
            "popular_cities": [],
            "education": [],
            "experience": [],
            "salary": [],
            "benefits": [],
            "similar": [],
        }

        relation_map = {
            "DEMANDS": ("skills", "核心技能"),
            "POPULAR_IN": ("popular_cities", "热门城市"),
            "COMMON_EDUCATION": ("education", "常见学历"),
            "COMMON_EXPERIENCE": ("experience", "常见经验"),
            "COMMON_SALARY": ("salary", "薪资分布"),
            "COMMON_BENEFIT": ("benefits", "常见福利"),
            "SIMILAR_TO": ("similar", "相似方向"),
        }

        for record in records:
            relation_type = record["relation_type"]
            node_name = record["node_name"]

            if not relation_type or not node_name:
                continue

            props = record["relation_properties"] or {}
            labels = record["node_labels"] or []

            node_type = labels[0] if labels else "Unknown"

            if relation_type == "SIMILAR_TO":
                percentage = float(
                    props.get("jaccard_pct") or 0
                )
                count = props.get("shared_jobs")
            else:
                percentage = float(
                    props.get("pct") or 0
                )
                count = props.get("job_count")

            group_name, chinese_name = relation_map[
                relation_type
            ]

            groups[group_name].append(
                {
                    "name": node_name,
                    "type": node_type,
                    "percentage": round(
                        percentage,
                        2,
                    ),
                    "count": count,
                    "relation_type": relation_type,
                    "relation_name": chinese_name,
                }
            )

        for group in groups.values():
            group.sort(
                key=lambda item: item["percentage"],
                reverse=True,
            )

        limits = {
            "skills": 5,
            "popular_cities": 3,
            "education": 2,
            "experience": 3,
            "salary": 2,
            "benefits": 3,
            "similar": 4,
        }

        for key in groups:
            groups[key] = groups[key][:limits[key]]

        nodes = [center]
        edges = []

        seen_nodes = {center["id"]}

        for group_items in groups.values():
            for item in group_items:
                node_id = (
                    f"{item['type']}:{item['name']}"
                )

                if node_id not in seen_nodes:
                    nodes.append(
                        {
                            "id": node_id,
                            "name": item["name"],
                            "type": item["type"],
                        }
                    )
                    seen_nodes.add(node_id)

                edges.append(
                    {
                        "source": center["id"],
                        "target": node_id,
                        "type": item["relation_type"],
                        "label": (
                            f"{item['relation_name']} "
                            f"{item['percentage']}%"
                        ),
                        "percentage": item[
                            "percentage"
                        ],
                    }
                )

        value_parts = []

        if groups["skills"]:
            skills = "、".join(
                item["name"]
                for item in groups["skills"]
            )

            value_parts.append(
                f"核心技能包括{skills}"
            )

        if groups["popular_cities"]:
            cities = "、".join(
                item["name"]
                for item in groups["popular_cities"]
            )

            value_parts.append(
                f"热门就业城市包括{cities}"
            )

        if groups["education"]:
            value_parts.append(
                "常见学历要求为"
                + groups["education"][0]["name"]
            )

        if groups["experience"]:
            value_parts.append(
                "常见经验要求为"
                + groups["experience"][0]["name"]
            )

        if center["salary_avg_k"]:
            value_parts.append(
                f"平均月薪约"
                f"{center['salary_avg_k']}K"
            )

        if groups["similar"]:
            names = "、".join(
                item["name"]
                for item in groups["similar"]
            )

            value_parts.append(
                f"还可以关注{names}等相近就业方向"
            )

        user_value = (
            "；".join(value_parts) + "。"
            if value_parts
            else ""
        )

        return {
            "keyword": keyword,
            "center": center,
            "groups": groups,
            "nodes": nodes,
            "edges": edges,
            "user_value": user_value,
        }


neo4j_service = Neo4jService()