"""CPubMed知识图谱检索器

基于RAG的医学知识图谱检索模块
"""
import pandas as pd
import pickle
import os
import sys
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

# 添加父目录到路径以导入logger_config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger_config import get_logger

logger = get_logger("kg_retriever")


class KGRetriever:
    """知识图谱检索器"""

    def __init__(self, data_dir: str):
        """初始化检索器

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.csv_path = self.data_dir / "CPubMed-kGv2_0.csv"
        self.index_path = self.data_dir / "kg_index.pkl"

        self.entity_index = None  # {entity_name: [triple_indices]}
        self.triples = None  # List of triples

    def build_index(self, force_rebuild: bool = False):
        """构建索引"""
        if not force_rebuild and self.index_path.exists():
            logger.info(f"加载已有索引: {self.index_path}")
            self._load_index()
            return

        logger.info(f"构建索引...")
        logger.info(f"读取数据: {self.csv_path}")

        # 读取CSV数据
        df = pd.read_csv(self.csv_path)
        logger.info(f"数据行数: {len(df)}")

        # 存储所有三元组
        self.triples = []
        self.entity_index = {}

        # 构建索引
        for idx, row in df.iterrows():
            head_full = row['head_entity@@entity_type']
            relation = row['relation']
            tail_full = row['tail_entity@@entity_type']

            # 跳过NaN值
            if pd.isna(head_full) or pd.isna(relation) or pd.isna(tail_full):
                continue

            # 确保为字符串类型
            head_full = str(head_full)
            relation = str(relation)
            tail_full = str(tail_full)

            # 解析实体和类型
            head_parts = head_full.split('@@')
            tail_parts = tail_full.split('@@')

            head_entity = head_parts[0] if len(head_parts) > 0 else head_full
            head_type = head_parts[1] if len(head_parts) > 1 else "未知"
            tail_entity = tail_parts[0] if len(tail_parts) > 0 else tail_full
            tail_type = tail_parts[1] if len(tail_parts) > 1 else "未知"

            triple = {
                'head_entity': head_entity,
                'head_type': head_type,
                'relation': relation,
                'tail_entity': tail_entity,
                'tail_type': tail_type,
                'index': idx
            }

            self.triples.append(triple)

            # 建立实体索引
            if head_entity not in self.entity_index:
                self.entity_index[head_entity] = []
            self.entity_index[head_entity].append(idx)

            if tail_entity not in self.entity_index:
                self.entity_index[tail_entity] = []
            self.entity_index[tail_entity].append(idx)

            if (idx + 1) % 100000 == 0:
                logger.info(f"已处理 {idx + 1} 行...")

        logger.info(f"索引构建完成")
        logger.info(f"三元组数: {len(self.triples)}")
        logger.info(f"唯一实体数: {len(self.entity_index)}")

        # 保存索引
        self._save_index()

    def _save_index(self):
        """保存索引到文件"""
        logger.info(f"保存索引到: {self.index_path}")
        with open(self.index_path, 'wb') as f:
            pickle.dump({
                'entity_index': self.entity_index,
                'triples': self.triples
            }, f)
        logger.info("索引保存完成")

    def _load_index(self):
        """从文件加载索引"""
        with open(self.index_path, 'rb') as f:
            data = pickle.load(f)
            self.entity_index = data['entity_index']
            self.triples = data['triples']
        logger.info(f"索引加载完成: {len(self.triples)} 三元组, {len(self.entity_index)} 实体")

    def search(self,
               entity: str,
               relation_filter: Optional[str] = None,
               entity_type_filter: Optional[str] = None,
               direction: str = "both",  # "head", "tail", "both"
               limit: int = 50) -> List[Dict[str, Any]]:
        """检索知识图谱

        Args:
            entity: 要查询的实体名称
            relation_filter: 关系类型过滤（可选）
            entity_type_filter: 实体类型过滤（可选）
            direction: 检索方向 - "head"(作为头实体), "tail"(作为尾实体), "both"(两者)
            limit: 返回结果数量限制

        Returns:
            匹配的三元组列表
        """
        if self.entity_index is None:
            raise RuntimeError("索引未构建，请先调用 build_index()")

        # 精确匹配
        if entity not in self.entity_index:
            # 尝试模糊匹配
            return self._fuzzy_search(entity, relation_filter, entity_type_filter, direction, limit)

        # 获取相关三元组索引
        triple_indices = self.entity_index[entity]

        results = []
        for idx in triple_indices:
            if idx >= len(self.triples):
                continue

            triple = self.triples[idx]

            # 方向过滤
            if direction == "head" and triple['head_entity'] != entity:
                continue
            if direction == "tail" and triple['tail_entity'] != entity:
                continue

            # 关系过滤
            if relation_filter and triple['relation'] != relation_filter:
                continue

            # 类型过滤
            if entity_type_filter:
                if triple['head_entity'] == entity and triple['head_type'] != entity_type_filter:
                    continue
                if triple['tail_entity'] == entity and triple['tail_type'] != entity_type_filter:
                    continue

            results.append(triple)

            if len(results) >= limit:
                break

        return results

    def _fuzzy_search(self,
                      entity: str,
                      relation_filter: Optional[str],
                      entity_type_filter: Optional[str],
                      direction: str,
                      limit: int) -> List[Dict[str, Any]]:
        """模糊搜索"""
        results = []
        entity_lower = entity.lower()

        # 找到包含查询实体的所有实体
        matching_entities = [
            e for e in self.entity_index.keys()
            if entity_lower in e.lower()
        ][:10]  # 限制模糊匹配的实体数量

        for matched_entity in matching_entities:
            partial_results = self.search(
                matched_entity,
                relation_filter,
                entity_type_filter,
                direction,
                limit - len(results)
            )
            results.extend(partial_results)

            if len(results) >= limit:
                break

        return results[:limit]

    def get_entity_relations(self, entity: str, limit: int = 20) -> Dict[str, List[Dict]]:
        """获取实体的所有关系，按关系类型分组

        Args:
            entity: 实体名称
            limit: 每种关系返回的最大数量

        Returns:
            按关系类型分组的三元组字典
        """
        triples = self.search(entity, limit=1000)

        # 按关系分组
        grouped = {}
        for triple in triples:
            rel = triple['relation']
            if rel not in grouped:
                grouped[rel] = []
            if len(grouped[rel]) < limit:
                grouped[rel].append(triple)

        return grouped

    def format_triples(self, triples: List[Dict[str, Any]]) -> str:
        """格式化三元组为可读文本

        Args:
            triples: 三元组列表

        Returns:
            格式化的文本
        """
        if not triples:
            return "未找到相关信息"

        lines = []
        for triple in triples:
            line = f"{triple['head_entity']}({triple['head_type']}) → {triple['relation']} → {triple['tail_entity']}({triple['tail_type']})"
            lines.append(line)

        return "\n".join(lines)
