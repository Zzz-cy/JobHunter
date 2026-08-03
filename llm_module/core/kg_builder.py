"""
知识图谱构建模块 - 构建和更新岗位能力知识图谱
支持Neo4j图数据库和内存存储
"""
import re
from typing import List, Dict, Optional, Any, Tuple
from models.schemas import Entity, Relation, ExtractedKnowledge, EntityType, RelationType, ONTOLOGY_CONSTRAINTS
from utils.logger import get_logger
logger = get_logger("core.kg_builder")

# 尝试导入Neo4j服务
try:
    from services.neo4j_service import get_neo4j_service, Neo4jService, Neo4jEntity, Neo4jRelation
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

# 尝试导入持久化服务
try:
    from services.persistence_service import get_persistence_service, DataPersistenceService
    PERSISTENCE_AVAILABLE = True
except ImportError:
    PERSISTENCE_AVAILABLE = False


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self):
        # 内存中的知识图谱
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []

        # 初始化Neo4j（如果可用）
        self.neo4j: Any = None
        if NEO4J_AVAILABLE:
            try:
                self.neo4j = get_neo4j_service()
                if self.neo4j.is_connected():
                    logger.info("Neo4j图数据库已连接")
                else:
                    logger.warning("Neo4j未连接，使用内存存储")
                    self.neo4j = None
            except Exception as e:
                logger.warning(f"Neo4j初始化失败: {e}")
                self.neo4j = None

        # 初始化持久化服务
        self.persistence: Any = None
        if PERSISTENCE_AVAILABLE:
            try:
                self.persistence = get_persistence_service()
                # 尝试加载已有数据
                self._load_from_persistence()
            except Exception as e:
                logger.warning(f"持久化服务初始化失败: {e}")
                self.persistence = None

    def _load_from_persistence(self):
        """从持久化存储加载数据"""
        if not self.persistence:
            return

        try:
            # 加载实体
            saved_entities = self.persistence.load_entities()
            if saved_entities:
                for key, entity_data in saved_entities.items():
                    try:
                        if isinstance(entity_data, dict):
                            from models.schemas import EntityType
                            entity = Entity(
                                name=entity_data.get("name", ""),
                                type=EntityType(entity_data.get("type", "skill")),
                                properties=entity_data.get("properties", {}),
                            )
                            self.entities[key] = entity
                    except Exception as e:
                        logger.warning(f"加载实体失败: {e}")
                logger.info(f"从持久化加载了 {len(self.entities)} 个实体")

            # 加载关系
            saved_relations = self.persistence.load_relations()
            if saved_relations:
                for rel_data in saved_relations:
                    try:
                        if isinstance(rel_data, dict):
                            from models.schemas import RelationType
                            relation = Relation(
                                source=rel_data.get("source", ""),
                                target=rel_data.get("target", ""),
                                type=RelationType(rel_data.get("type", "requires")),
                                properties=rel_data.get("properties", {}),
                            )
                            self.relations.append(relation)
                    except Exception as e:
                        logger.warning(f"加载关系失败: {e}")
                logger.info(f"从持久化加载了 {len(self.relations)} 个关系")

        except Exception as e:
            logger.warning(f"从持久化加载数据失败: {e}")

    def add_entities(self, entities: List[Entity]) -> None:
        """
        添加实体到知识图谱

        Args:
            entities: 实体列表
        """
        for entity in entities:
            key = f"{entity.name}:{entity.type.value}"
            if key not in self.entities:
                self.entities[key] = entity
                logger.info(f"添加实体: {entity.name} ({entity.type.value})")
            else:
                # 合并属性
                self.entities[key].properties.update(entity.properties)
                logger.info(f"更新实体: {entity.name}")

            # 同步到Neo4j
            if self.neo4j and NEO4J_AVAILABLE:
                try:
                    neo4j_entity = Neo4jEntity(
                        name=entity.name,
                        type=entity.type.value,
                        properties=entity.properties,
                    )
                    self.neo4j.create_entity(neo4j_entity)
                except Exception as e:
                    logger.warning(f"Neo4j实体同步失败: {e}")

    def add_relations(self, relations: List[Relation]) -> None:
        """
        添加关系

        Args:
            relations: 关系列表
        """
        for relation in relations:
            # 简单去重
            exists = any(
                r.source == relation.source and
                r.target == relation.target and
                r.type == relation.type
                for r in self.relations
            )

            if not exists:
                self.relations.append(relation)
                logger.info(f"添加关系: {relation.source} --{relation.type.value}--> {relation.target}")

                # 同步到Neo4j
                if self.neo4j and NEO4J_AVAILABLE:
                    try:
                        neo4j_relation = Neo4jRelation(
                            source=relation.source,
                            target=relation.target,
                            type=relation.type.value,
                        )
                        self.neo4j.create_relation(neo4j_relation)
                    except Exception as e:
                        logger.warning(f"Neo4j关系同步失败: {e}")

    def build_from_knowledge(self, knowledge: ExtractedKnowledge) -> None:
        """
        从抽取的知识构建知识图谱

        Args:
            knowledge: 抽取的知识
        """
        logger.info("开始构建知识图谱...")

        # 添加实体
        self.add_entities(knowledge.entities)

        # 添加关系
        self.add_relations(knowledge.relations)

        logger.info(f"知识图谱构建完成: {len(self.entities)}实体, {len(self.relations)}关系")

    def save_to_persistence(self) -> bool:
        """保存知识图谱到持久化存储"""
        if not self.persistence:
            logger.warning("持久化服务不可用，无法保存")
            return False

        try:
            # 保存实体
            entities_data = {}
            for key, entity in self.entities.items():
                entities_data[key] = {
                    "name": entity.name,
                    "type": entity.type.value,
                    "properties": entity.properties,
                }
            self.persistence.save_entities(entities_data)

            # 保存关系
            self.persistence.save_relations(self.relations)

            # 保存完整知识图谱
            kg_data = {
                "entity_count": len(self.entities),
                "relation_count": len(self.relations),
                "entities": entities_data,
            }
            self.persistence.save_knowledge_graph(kg_data)

            logger.info("知识图谱已保存到持久化存储")
            return True
        except Exception as e:
            logger.error(f"保存到持久化失败: {e}")
            return False

    def export_to_json(self, filepath: str) -> bool:
        """导出知识图谱到JSON文件"""
        try:
            if self.persistence:
                return self.persistence.export_to_json(filepath)
            return False
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False

    def query_entities(
        self,
        entity_type: Optional[str] = None,
        name_contains: Optional[str] = None,
    ) -> List[Entity]:
        """
        查询实体

        Args:
            entity_type: 实体类型过滤
            name_contains: 名称包含过滤

        Returns:
            实体列表
        """
        results = []
        for entity in self.entities.values():
            if entity_type and entity.type.value != entity_type:
                continue
            if name_contains and name_contains not in entity.name:
                continue
            results.append(entity)
        return results

    def query_relations(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> List[Relation]:
        """
        查询关系

        Args:
            source: 源实体过滤
            target: 目标实体过滤
            relation_type: 关系类型过滤

        Returns:
            关系列表
        """
        results = []
        for relation in self.relations:
            if source and relation.source != source:
                continue
            if target and relation.target != target:
                continue
            if relation_type and relation.type.value != relation_type:
                continue
            results.append(relation)
        return results

    def get_subgraph(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """
        获取某个实体的子图

        Args:
            entity_name: 实体名称
            depth: 搜索深度

        Returns:
            子图数据
        """
        # 找到相关实体和关系
        related_entities: List[Entity] = []
        related_relations = []

        current_level = {entity_name}
        visited = {entity_name}

        for _ in range(depth):
            next_level = set()
            for name in current_level:
                for relation in self.relations:
                    if relation.source == name and relation.target not in visited:
                        related_relations.append(relation)
                        next_level.add(relation.target)
                        visited.add(relation.target)
                    elif relation.target == name and relation.source not in visited:
                        related_relations.append(relation)
                        next_level.add(relation.source)
                        visited.add(relation.source)
            current_level = next_level

        # 收集所有相关实体 (使用列表+去重，避免set的hash问题)
        seen_keys = set()
        for relation in related_relations:
            for key in [f"{relation.source}:job", f"{relation.source}:skill",
                       f"{relation.target}:job", f"{relation.target}:skill",
                       f"{relation.source}:tool", f"{relation.source}:knowledge",
                       f"{relation.target}:tool", f"{relation.target}:knowledge"]:
                if key in self.entities and key not in seen_keys:
                    related_entities.append(self.entities[key])
                    seen_keys.add(key)

        return {
            "center": entity_name,
            "entities": [e.model_dump() for e in related_entities],
            "relations": [r.model_dump() for r in related_relations],
        }

    def export_to_json(self) -> Dict[str, Any]:
        """
        导出知识图谱为JSON

        Returns:
            JSON数据
        """
        return {
            "entities": [e.model_dump() for e in self.entities.values()],
            "relations": [r.model_dump() for r in self.relations],
        }

    def import_from_json(self, data: Dict[str, Any]) -> None:
        """
        从JSON导入知识图谱

        Args:
            data: JSON数据
        """
        for e in data.get("entities", []):
            entity = Entity(**e)
            self.entities[f"{entity.name}:{entity.type.value}"] = entity

        for r in data.get("relations", []):
            self.relations.append(Relation(**r))

        logger.info(f"导入知识图谱: {len(self.entities)}实体, {len(self.relations)}关系")

    # ==================== 图谱质量校验 ====================

    def validate_graph(self, industry: str = "") -> Dict[str, Any]:
        """
        执行全面的图谱质量校验

        Args:
            industry: 行业上下文，用于行业特定的本体约束

        Returns:
            校验报告 {
                "is_valid": bool,
                "total_entities": int,
                "total_relations": int,
                "issues": [...],
                "stats": {...}
            }
        """
        issues = []

        # 1. 实体解析/去重检查
        duplicate_issues = self._check_entity_duplicates()
        issues.extend(duplicate_issues)

        # 2. 关系一致性检查（本体约束）
        consistency_issues = self._check_relation_consistency(industry)
        issues.extend(consistency_issues)

        # 3. 孤立节点检测
        orphan_issues = self._check_orphan_nodes()
        issues.extend(orphan_issues)

        # 4. 置信度过滤
        low_confidence_issues = self._check_low_confidence()
        issues.extend(low_confidence_issues)

        # 5. 冲突检测
        conflict_issues = self._check_conflicts()
        issues.extend(conflict_issues)

        # 6. 完整性检查（关系引用的实体是否存在）
        integrity_issues = self._check_referential_integrity()
        issues.extend(integrity_issues)

        # 统计信息
        stats = self._compute_graph_stats()

        return {
            "is_valid": len(issues) == 0,
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "issues": issues,
            "issue_count": len(issues),
            "stats": stats,
        }

    def _check_entity_duplicates(self) -> List[Dict[str, Any]]:
        """检查实体重复（模糊匹配）"""
        issues = []
        names_lower = {}  # name_lower -> list of (key, entity)

        for key, entity in self.entities.items():
            name_lower = entity.name.lower().strip()
            # 去除常见变体：空格、连字符、版本号
            normalized = re.sub(r'[\s\-_]', '', name_lower)
            normalized = re.sub(r'v?\d+(\.\d+)*$', '', normalized).strip()

            if normalized not in names_lower:
                names_lower[normalized] = []
            names_lower[normalized].append((key, entity))

        for normalized, entries in names_lower.items():
            if len(entries) > 1:
                names = [e.name for _, e in entries]
                issues.append({
                    "type": "duplicate_entity",
                    "severity": "warning",
                    "message": f"疑似重复实体: {names}",
                    "entities": names,
                    "suggestion": f"建议合并为统一名称",
                })

        return issues

    def _check_relation_consistency(self, industry: str = "") -> List[Dict[str, Any]]:
        """检查关系是否符合本体约束"""
        issues = []

        # 获取行业特定的约束（如果有）
        from utils.config import INDUSTRY_ONTOLOGY
        industry_ontology = INDUSTRY_ONTOLOGY.get(industry, {})
        industry_constraints = industry_ontology.get("relation_constraints", {})

        for relation in self.relations:
            # 查找源实体和目标实体的类型
            source_type = self._get_entity_type(relation.source)
            target_type = self._get_entity_type(relation.target)
            rel_type = relation.type.value

            if not source_type or not target_type:
                continue  # 实体不存在的问题在完整性检查中报告

            # 检查全局本体约束
            constraint_key = (source_type, rel_type)
            allowed_targets = ONTOLOGY_CONSTRAINTS.get(constraint_key, None)

            if allowed_targets is not None and target_type not in allowed_targets:
                issues.append({
                    "type": "relation_consistency",
                    "severity": "error",
                    "message": f"关系类型不匹配: ({source_type})-{rel_type}->({target_type})，"
                               f"允许的目标类型: {allowed_targets}",
                    "relation": f"{relation.source} --{rel_type}--> {relation.target}",
                    "suggestion": f"检查关系类型是否正确，或更新本体约束",
                })

            # 检查行业特定约束
            if industry_constraints:
                ind_constraint_key = (source_type, rel_type)
                ind_allowed = industry_constraints.get(ind_constraint_key, None)
                if ind_allowed is not None and target_type not in ind_allowed:
                    issues.append({
                        "type": "industry_consistency",
                        "severity": "warning",
                        "message": f"行业({industry})约束不匹配: ({source_type})-{rel_type}->({target_type})",
                        "relation": f"{relation.source} --{rel_type}--> {relation.target}",
                    })

        return issues

    def _check_orphan_nodes(self) -> List[Dict[str, Any]]:
        """检测孤立节点（没有任何关系的实体）"""
        issues = []

        # 收集所有有关系引用的实体名称
        connected_entities = set()
        for relation in self.relations:
            connected_entities.add(relation.source)
            connected_entities.add(relation.target)

        # 检查每个实体是否被关系连接
        for key, entity in self.entities.items():
            if entity.name not in connected_entities:
                # INDUSTRY类型实体允许孤立（作为分类节点）
                if entity.type != EntityType.INDUSTRY:
                    issues.append({
                        "type": "orphan_node",
                        "severity": "warning",
                        "message": f"孤立实体: {entity.name} ({entity.type.value})，无任何关系连接",
                        "entity": entity.name,
                        "suggestion": "考虑添加关系或删除该实体",
                    })

        return issues

    def _check_low_confidence(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """检查低置信度关系"""
        issues = []

        for relation in self.relations:
            if relation.confidence < threshold:
                issues.append({
                    "type": "low_confidence",
                    "severity": "info",
                    "message": f"低置信度关系: {relation.source} --{relation.type.value}--> {relation.target} "
                               f"(confidence={relation.confidence:.2f})",
                    "relation": f"{relation.source} --{relation.type.value}--> {relation.target}",
                    "confidence": relation.confidence,
                    "suggestion": f"建议人工审核或补充证据提升置信度",
                })

        return issues

    def _check_conflicts(self) -> List[Dict[str, Any]]:
        """检测矛盾关系"""
        issues = []

        # 按源-目标对分组关系
        pair_relations: Dict[Tuple[str, str], List[Relation]] = {}
        for relation in self.relations:
            key = (relation.source, relation.target)
            if key not in pair_relations:
                pair_relations[key] = []
            pair_relations[key].append(relation)

        # 检查同一对实体间是否有矛盾关系
        # 例如：A requires B 和 A 不需要 B（如果未来添加否定关系）
        # 目前检查：同一对实体间是否有语义冲突的关系类型
        conflict_pairs = {
            ("requires", "similar_to"),  # 要求关系和相似关系语义冲突
            ("leads_to", "similar_to"),  # 晋升路径和相似关系语义冲突
        }

        for (source, target), rels in pair_relations.items():
            if len(rels) > 1:
                rel_types = [r.type.value for r in rels]
                for pair in conflict_pairs:
                    if pair[0] in rel_types and pair[1] in rel_types:
                        issues.append({
                            "type": "conflict_relation",
                            "severity": "warning",
                            "message": f"矛盾关系: {source} 和 {target} 之间同时存在 "
                                       f"{pair[0]} 和 {pair[1]} 关系",
                            "entity_pair": f"{source} <-> {target}",
                            "conflict_types": list(pair),
                            "suggestion": "检查关系类型是否正确，移除矛盾关系",
                        })

        return issues

    def _check_referential_integrity(self) -> List[Dict[str, Any]]:
        """检查关系引用的实体是否存在"""
        issues = []
        entity_names = {entity.name for entity in self.entities.values()}

        for relation in self.relations:
            if relation.source not in entity_names:
                issues.append({
                    "type": "missing_source_entity",
                    "severity": "error",
                    "message": f"关系引用的源实体不存在: {relation.source}",
                    "relation": f"{relation.source} --{relation.type.value}--> {relation.target}",
                    "suggestion": f"创建实体 '{relation.source}' 或删除该关系",
                })
            if relation.target not in entity_names:
                issues.append({
                    "type": "missing_target_entity",
                    "severity": "error",
                    "message": f"关系引用的目标实体不存在: {relation.target}",
                    "relation": f"{relation.source} --{relation.type.value}--> {relation.target}",
                    "suggestion": f"创建实体 '{relation.target}' 或删除该关系",
                })

        return issues

    def _get_entity_type(self, name: str) -> Optional[str]:
        """获取实体类型"""
        for key, entity in self.entities.items():
            if entity.name == name:
                return entity.type.value
        return None

    def _compute_graph_stats(self) -> Dict[str, Any]:
        """计算图谱统计指标"""
        # 实体类型分布
        type_dist: Dict[str, int] = {}
        for entity in self.entities.values():
            t = entity.type.value
            type_dist[t] = type_dist.get(t, 0) + 1

        # 关系类型分布
        rel_type_dist: Dict[str, int] = {}
        for relation in self.relations:
            t = relation.type.value
            rel_type_dist[t] = rel_type_dist.get(t, 0) + 1

        # 图密度 = 实际关系数 / 最大可能关系数
        n = len(self.entities)
        max_relations = n * (n - 1) if n > 1 else 1
        density = len(self.relations) / max_relations if max_relations > 0 else 0

        # 平均度
        degree_map: Dict[str, int] = {}
        for relation in self.relations:
            degree_map[relation.source] = degree_map.get(relation.source, 0) + 1
            degree_map[relation.target] = degree_map.get(relation.target, 0) + 1
        avg_degree = sum(degree_map.values()) / len(degree_map) if degree_map else 0

        # 平均置信度
        avg_confidence = (
            sum(r.confidence for r in self.relations) / len(self.relations)
            if self.relations else 0
        )

        return {
            "entity_type_distribution": type_dist,
            "relation_type_distribution": rel_type_dist,
            "density": round(density, 6),
            "average_degree": round(avg_degree, 2),
            "average_confidence": round(avg_confidence, 3),
            "orphan_ratio": round(
                (n - len(degree_map)) / n if n > 0 else 0, 3
            ),
        }

    def fix_common_issues(self) -> Dict[str, int]:
        """
        自动修复常见图谱质量问题

        Returns:
            修复统计 {"removed_orphans": N, "removed_invalid_relations": N, ...}
        """
        fixes = {
            "removed_orphans": 0,
            "removed_invalid_relations": 0,
            "merged_duplicates": 0,
        }

        # 1. 移除引用不存在实体的关系
        entity_names = {entity.name for entity in self.entities.values()}
        valid_relations = []
        for relation in self.relations:
            if relation.source in entity_names and relation.target in entity_names:
                valid_relations.append(relation)
            else:
                fixes["removed_invalid_relations"] += 1
                logger.info(f"移除无效关系: {relation.source} --{relation.type.value}--> {relation.target}")
        self.relations = valid_relations

        # 2. 合并简单重复实体（完全相同名称，不同大小写）
        seen_names = {}
        to_remove = []
        for key, entity in self.entities.items():
            name_lower = entity.name.lower().strip()
            if name_lower in seen_names:
                # 保留先出现的，合并属性
                existing_key = seen_names[name_lower]
                self.entities[existing_key].properties.update(entity.properties)
                to_remove.append(key)
                fixes["merged_duplicates"] += 1
                # 更新关系中的引用
                for relation in self.relations:
                    if relation.source == entity.name:
                        relation.source = self.entities[existing_key].name
                    if relation.target == entity.name:
                        relation.target = self.entities[existing_key].name
            else:
                seen_names[name_lower] = key

        for key in to_remove:
            del self.entities[key]

        # 3. 移除孤立节点（非INDUSTRY类型）
        connected = set()
        for relation in self.relations:
            connected.add(relation.source)
            connected.add(relation.target)

        orphan_keys = []
        for key, entity in self.entities.items():
            if entity.name not in connected and entity.type != EntityType.INDUSTRY:
                orphan_keys.append(key)
                fixes["removed_orphans"] += 1

        for key in orphan_keys:
            logger.info(f"移除孤立实体: {key}")
            del self.entities[key]

        logger.info(f"图谱修复完成: {fixes}")
        return fixes


# 单例
_kg_builder: Any = None


def get_kg_builder() -> KnowledgeGraphBuilder:
    """获取知识图谱构建器单例"""
    global _kg_builder
    if _kg_builder is None:
        _kg_builder = KnowledgeGraphBuilder()
    return _kg_builder
