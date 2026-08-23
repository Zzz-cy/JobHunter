"""
数据持久化服务 - 将知识图谱数据持久化到文件
支持JSON格式存储，便于备份和迁移
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from utils.config import BASE_DIR
from utils.logger import get_logger
logger = get_logger("services.persistence_service")


class DataPersistenceService:
    """数据持久化服务"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(BASE_DIR / "data" / "persist")

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据文件路径
        self.entities_file = self.data_dir / "entities.json"
        self.relations_file = self.data_dir / "relations.json"
        self.jobs_file = self.data_dir / "jobs.json"
        self.skills_file = self.data_dir / "skills.json"
        self.stats_file = self.data_dir / "stats.json"

        logger.info(f"数据持久化目录: {self.data_dir}")

    def save_entities(self, entities: Dict[str, Any]) -> bool:
        """保存实体数据"""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "count": len(entities),
                "entities": entities,
            }
            with open(self.entities_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"实体数据已保存: {len(entities)}个")
            return True
        except Exception as e:
            logger.error(f"保存实体失败: {e}")
            return False

    def load_entities(self) -> Optional[Dict[str, Any]]:
        """加载实体数据"""
        try:
            if not self.entities_file.exists():
                return None

            with open(self.entities_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"实体数据已加载: {data.get('count', 0)}个")
            return data.get("entities", {})
        except Exception as e:
            logger.error(f"加载实体失败: {e}")
            return None

    def save_relations(self, relations: list) -> bool:
        """保存关系数据"""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "count": len(relations),
                "relations": [r.model_dump() if hasattr(r, "model_dump") else r for r in relations],
            }
            with open(self.relations_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"关系数据已保存: {len(relations)}个")
            return True
        except Exception as e:
            logger.error(f"保存关系失败: {e}")
            return False

    def load_relations(self) -> Optional[list]:
        """加载关系数据"""
        try:
            if not self.relations_file.exists():
                return None

            with open(self.relations_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"关系数据已加载: {data.get('count', 0)}个")
            return data.get("relations", [])
        except Exception as e:
            logger.error(f"加载关系失败: {e}")
            return None

    def save_knowledge_graph(self, kg_data: Dict[str, Any]) -> bool:
        """保存完整知识图谱"""
        try:
            file_path = self.data_dir / "knowledge_graph.json"
            data = {
                "updated_at": datetime.now().isoformat(),
                **kg_data,
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("知识图谱已保存")
            return True
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
            return False

    def load_knowledge_graph(self) -> Optional[Dict[str, Any]]:
        """加载完整知识图谱"""
        try:
            file_path = self.data_dir / "knowledge_graph.json"
            if not file_path.exists():
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("知识图谱已加载")
            return data
        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")
            return None

    def save_stats(self, stats: Dict[str, Any]) -> bool:
        """保存统计数据"""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                **stats,
            }
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存统计失败: {e}")
            return False

    def export_to_json(self, filepath: str) -> bool:
        """导出所有数据到JSON文件"""
        try:
            data = {
                "export_time": datetime.now().isoformat(),
                "entities": self.load_entities() or {},
                "relations": self.load_relations() or [],
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"数据已导出到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False

    def import_from_json(self, filepath: str) -> Optional[Dict[str, Any]]:
        """从JSON文件导入数据"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "entities" in data:
                self.save_entities(data["entities"])

            if "relations" in data:
                self.save_relations(data["relations"])

            logger.info(f"数据已从 {filepath} 导入")
            return data
        except Exception as e:
            logger.error(f"导入失败: {e}")
            return None


# 单例
_persist_service: Any = None


def get_persistence_service() -> DataPersistenceService:
    """获取持久化服务单例"""
    global _persist_service
    if _persist_service is None:
        _persist_service = DataPersistenceService()
    return _persist_service
