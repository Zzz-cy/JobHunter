"""
Neo4j图数据库服务 - 持久化存储知识图谱
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

from utils.logger import get_logger
logger = get_logger("services.neo4j_service")

try:
    from neo4j import GraphDatabase, Driver, Session
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("Neo4j驱动未安装，将使用内存存储")

from utils.config import NEO4J_CONFIG


@dataclass
class Neo4jEntity:
    """Neo4j实体"""
    name: str
    type: str
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class Neo4jRelation:
    """Neo4j关系"""
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class Neo4jService:
    """Neo4j图数据库服务"""

    def __init__(self):
        self.driver: Optional[Any] = None
        self.uri = NEO4J_CONFIG["uri"]
        self.user = NEO4J_CONFIG["user"]
        self.password = NEO4J_CONFIG["password"]

        if NEO4J_AVAILABLE:
            # 先快速检测端口是否可达，避免长时间等待连接超时
            if not self._is_port_open():
                logger.warning(f"Neo4j端口不可达: {self.uri}，跳过连接")
            else:
                try:
                    self.driver = GraphDatabase.driver(
                        self.uri,
                        auth=(self.user, self.password),
                        connection_timeout=3,
                    )
                    # 测试连接
                    with self.driver.session() as session:
                        session.run("RETURN 1")
                    logger.info(f"Neo4j连接成功: {self.uri}")
                except Exception as e:
                    logger.error(f"Neo4j连接失败: {e}")
                    self.driver = None
        else:
            logger.warning("Neo4j驱动不可用")

    def _is_port_open(self) -> bool:
        """快速检测Neo4j端口是否可达（1秒超时）"""
        import socket
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.uri)
            host = parsed.hostname or "localhost"
            port = parsed.port or 7687
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.driver is not None

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.driver = None

    def create_entity(self, entity: Neo4jEntity) -> bool:
        """
        创建实体节点

        Args:
            entity: 实体信息

        Returns:
            是否成功
        """
        if not self.driver:
            logger.warning("Neo4j未连接，跳过创建实体")
            return False

        try:
            with self.driver.session() as session:
                # 使用MERGE避免重复创建
                query = f"""
                MERGE (e:{entity.type} {{name: $name}})
                SET e += $properties
                RETURN e
                """
                session.run(query, name=entity.name, properties=entity.properties)
                logger.info(f"创建实体: {entity.name} ({entity.type})")
                return True
        except Exception as e:
            logger.error(f"创建实体失败: {e}")
            return False

    def create_relation(self, relation: Neo4jRelation) -> bool:
        """
        创建关系

        Args:
            relation: 关系信息

        Returns:
            是否成功
        """
        if not self.driver:
            logger.warning("Neo4j未连接，跳过创建关系")
            return False

        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (a {{name: $source}}), (b {{name: $target}})
                MERGE (a)-[r:{relation.type}]->(b)
                SET r += $properties
                RETURN r
                """
                session.run(
                    query,
                    source=relation.source,
                    target=relation.target,
                    properties=relation.properties,
                )
                logger.info(f"创建关系: {relation.source} --{relation.type}--> {relation.target}")
                return True
        except Exception as e:
            logger.error(f"创建关系失败: {e}")
            return False

    def find_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """
        查找实体

        Args:
            name: 实体名称

        Returns:
            实体信息
        """
        if not self.driver:
            return None

        try:
            with self.driver.session() as session:
                query = "MATCH (e {name: $name}) RETURN e"
                result = session.run(query, name=name)
                record = result.single()
                if record:
                    return dict(record["e"])
                return None
        except Exception as e:
            logger.error(f"查找实体失败: {e}")
            return None

    def find_neighbors(self, name: str, depth: int = 1) -> Dict[str, Any]:
        """
        查找邻居节点

        Args:
            name: 实体名称
            depth: 搜索深度

        Returns:
            邻居节点和关系
        """
        if not self.driver:
            return {"entities": [], "relations": []}

        try:
            with self.driver.session() as session:
                query = """
                MATCH path = (start {name: $name})-[*1..%d]-(neighbor)
                RETURN start, neighbor, relationships(path) as rels
                LIMIT 100
                """ % depth

                result = session.run(query, name=name)

                entities = set()
                relations = []

                for record in result:
                    start = record["start"]
                    neighbor = record["neighbor"]
                    rels = record["rels"]

                    entities.add((start["name"], start.get("type", "unknown")))
                    entities.add((neighbor["name"], neighbor.get("type", "unknown")))

                    for rel in rels:
                        relations.append({
                            "source": rel.start_node["name"],
                            "target": rel.end_node["name"],
                            "type": rel.type,
                        })

                return {
                    "entities": [{"name": e[0], "type": e[1]} for e in entities],
                    "relations": relations,
                }
        except Exception as e:
            logger.error(f"查找邻居失败: {e}")
            return {"entities": [], "relations": []}

    def search_by_type(self, entity_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        按类型搜索实体

        Args:
            entity_type: 实体类型
            limit: 返回数量限制

        Returns:
            实体列表
        """
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (e:{entity_type})
                RETURN e
                LIMIT $limit
                """
                result = session.run(query, limit=limit)
                return [dict(record["e"]) for record in result]
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行原始Cypher查询

        Args:
            query: Cypher查询语句
            parameters: 查询参数

        Returns:
            查询结果
        """
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Cypher查询失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if not self.driver:
            return {"connected": False}

        try:
            with self.driver.session() as session:
                # 统计各类节点数量
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as type, count(n) as count
                    ORDER BY count DESC
                """)
                node_stats = {record["type"]: record["count"] for record in result}

                # 统计关系数量
                rel_result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                    ORDER BY count DESC
                """)
                rel_stats = {record["type"]: record["count"] for record in rel_result}

                return {
                    "connected": True,
                    "node_counts": node_stats,
                    "relation_counts": rel_stats,
                }
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {"connected": True, "error": str(e)}

    # ==================== 图谱推理 ====================

    def infer_transitive_prerequisites(self, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        传递推理：如果 A prerequisite B, B prerequisite C，则 A 是 C 的间接前置

        Args:
            max_depth: 最大推理深度

        Returns:
            推导出的新关系列表
        """
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                # 查找所有传递前置链
                query = f"""
                MATCH path = (a:skill)-[:prerequisite*2..{max_depth}]->(c:skill)
                WHERE NOT (a)-[:prerequisite]->(c)
                RETURN a.name as source, c.name as target, length(path) as depth
                """
                result = session.run(query)
                inferred = []
                for record in result:
                    inferred.append({
                        "source": record["source"],
                        "target": record["target"],
                        "type": "prerequisite",
                        "inferred": True,
                        "depth": record["depth"],
                        "reasoning": f"传递推理: {record['source']} 通过 {record['depth']} 步前置链间接前置于 {record['target']}",
                    })
                logger.info(f"传递推理发现 {len(inferred)} 条隐含前置关系")
                return inferred
        except Exception as e:
            logger.error(f"传递推理失败: {e}")
            return []

    def infer_skill_requirements(self, job_name: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        路径推理：从岗位出发，推导出所有直接和间接需要的技能

        Args:
            job_name: 岗位名称
            max_depth: 最大推理深度

        Returns:
            {
                "job": str,
                "direct_skills": [...],
                "indirect_skills": [...],
                "skill_paths": [...]
            }
        """
        if not self.driver:
            return {"job": job_name, "direct_skills": [], "indirect_skills": [], "skill_paths": []}

        try:
            with self.driver.session() as session:
                # 直接技能
                direct_query = """
                MATCH (j:job {name: $name})-[:requires]->(s:skill)
                RETURN s.name as skill, s.type as type
                """
                direct_result = session.run(direct_query, name=job_name)
                direct_skills = [{"name": r["skill"], "type": r.get("type", "skill")} for r in direct_result]

                # 间接技能（通过前置链推导）
                indirect_query = f"""
                MATCH path = (j:job {{name: $name}})-[:requires]->(s1:skill)-[:prerequisite*1..{max_depth}]->(s2:skill)
                WHERE NOT (j)-[:requires]->(s2)
                RETURN s2.name as skill, s1.name as via_skill, length(path) as depth
                """
                indirect_result = session.run(indirect_query, name=job_name)
                indirect_skills = []
                seen = set()
                for r in indirect_result:
                    skill_name = r["skill"]
                    if skill_name not in seen:
                        seen.add(skill_name)
                        indirect_skills.append({
                            "name": skill_name,
                            "via": r["via_skill"],
                            "depth": r["depth"],
                            "reasoning": f"岗位要求 {r['via_skill']}，而 {r['via_skill']} 的前置技能是 {skill_name}",
                        })

                # 技能路径（从入门到高级的技能链）
                path_query = f"""
                MATCH path = (j:job {{name: $name}})-[:requires]->(s1:skill)-[:prerequisite*1..{max_depth}]->(s2:skill)
                RETURN [n in nodes(path) | n.name] as names, length(path) as depth
                ORDER BY depth
                """
                path_result = session.run(path_query, name=job_name)
                skill_paths = []
                for r in path_result:
                    skill_paths.append({
                        "path": r["names"],
                        "depth": r["depth"],
                    })

                return {
                    "job": job_name,
                    "direct_skills": direct_skills,
                    "indirect_skills": indirect_skills,
                    "skill_paths": skill_paths,
                }
        except Exception as e:
            logger.error(f"技能路径推理失败: {e}")
            return {"job": job_name, "direct_skills": [], "indirect_skills": [], "skill_paths": []}

    def infer_similar_job_skills(self, job_name: str) -> Dict[str, Any]:
        """
        类比推理：通过相似岗位推导技能需求
        如果 A similar_to B，且 B requires skill_X，则 A 可能也需要 skill_X

        Args:
            job_name: 岗位名称

        Returns:
            {
                "job": str,
                "similar_jobs": [...],
                "inferred_skills": [...]
            }
        """
        if not self.driver:
            return {"job": job_name, "similar_jobs": [], "inferred_skills": []}

        try:
            with self.driver.session() as session:
                # 查找相似岗位及其技能
                query = """
                MATCH (j1:job {name: $name})-[:similar_to]-(j2:job)
                OPTIONAL MATCH (j2)-[:requires]->(s:skill)
                WHERE NOT (j1)-[:requires]->(s)
                RETURN j2.name as similar_job,
                       collect({name: s.name, type: s.type}) as inferred_skills
                """
                result = session.run(query, name=job_name)

                similar_jobs = []
                all_inferred = []
                seen_skills = set()

                for record in result:
                    similar_job = record["similar_job"]
                    skills = record["inferred_skills"]
                    similar_jobs.append(similar_job)
                    for skill in skills:
                        if skill["name"] and skill["name"] not in seen_skills:
                            seen_skills.add(skill["name"])
                            all_inferred.append({
                                "name": skill["name"],
                                "type": skill.get("type", "skill"),
                                "inferred_from": similar_job,
                                "reasoning": f"相似岗位 {similar_job} 需要该技能",
                            })

                return {
                    "job": job_name,
                    "similar_jobs": similar_jobs,
                    "inferred_skills": all_inferred,
                }
        except Exception as e:
            logger.error(f"类比推理失败: {e}")
            return {"job": job_name, "similar_jobs": [], "inferred_skills": []}

    def infer_career_paths(self, job_name: str, max_depth: int = 4) -> Dict[str, Any]:
        """
        职业路径推理：通过 leads_to 关系推导职业晋升路径

        Args:
            job_name: 起始岗位名称
            max_depth: 最大推理深度

        Returns:
            {
                "start_job": str,
                "career_paths": [[job1, job2, ...], ...],
                "skills_along_path": [...]
            }
        """
        if not self.driver:
            return {"start_job": job_name, "career_paths": [], "skills_along_path": []}

        try:
            with self.driver.session() as session:
                # 查找所有晋升路径
                query = f"""
                MATCH path = (j1:job {{name: $name}})-[:leads_to*1..{max_depth}]->(jn:job)
                RETURN [n in nodes(path) | n.name] as career_path,
                       length(path) as depth
                ORDER BY depth
                """
                result = session.run(query, name=job_name)

                career_paths = []
                for record in result:
                    career_paths.append({
                        "path": record["career_path"],
                        "depth": record["depth"],
                    })

                # 沿路径的技能需求
                skills_query = f"""
                MATCH path = (j1:job {{name: $name}})-[:leads_to*1..{max_depth}]->(jn:job)
                UNWIND nodes(path) as job
                OPTIONAL MATCH (job)-[:requires]->(s:skill)
                RETURN job.name as job, collect(DISTINCT s.name) as skills
                """
                skills_result = session.run(skills_query, name=job_name)
                skills_along_path = {}
                for record in skills_result:
                    job = record["job"]
                    skills = record["skills"]
                    if skills:
                        skills_along_path[job] = skills

                return {
                    "start_job": job_name,
                    "career_paths": career_paths,
                    "skills_along_path": skills_along_path,
                }
        except Exception as e:
            logger.error(f"职业路径推理失败: {e}")
            return {"start_job": job_name, "career_paths": [], "skills_along_path": []}

    def apply_inferred_relations(self, inferred_relations: List[Dict[str, Any]]) -> int:
        """
        将推理结果写入图谱（添加 INFERRED 标签和低置信度）

        Args:
            inferred_relations: 推理得到的关系列表

        Returns:
            成功写入的关系数量
        """
        if not self.driver:
            return 0

        count = 0
        for rel in inferred_relations:
            try:
                with self.driver.session() as session:
                    query = """
                    MATCH (a {name: $source}), (b {name: $target})
                    MERGE (a)-[r:prerequisite {inferred: true}]->(b)
                    SET r.confidence = 0.5,
                        r.reasoning = $reasoning,
                        r.inferred_depth = $depth
                    RETURN r
                    """
                    session.run(
                        query,
                        source=rel["source"],
                        target=rel["target"],
                        reasoning=rel.get("reasoning", ""),
                        depth=rel.get("depth", 1),
                    )
                    count += 1
            except Exception as e:
                logger.warning(f"写入推理关系失败: {e}")

        logger.info(f"写入 {count} 条推理关系")
        return count

    def clear_database(self) -> bool:
        """
        清空数据库（危险操作！）

        Returns:
            是否成功
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.warning("数据库已清空！")
                return True
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            return False


# 单例
_neo4j_service: Any = None


def get_neo4j_service() -> Neo4jService:
    """获取Neo4j服务单例"""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service
