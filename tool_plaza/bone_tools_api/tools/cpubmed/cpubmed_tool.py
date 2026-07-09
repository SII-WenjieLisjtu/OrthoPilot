"""CPubMed知识图谱检索工具

供大模型调用的医学知识图谱检索工具
"""
import os
import json
from typing import Any, Dict, List
from pathlib import Path
import sys

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from base import Tool, ToolParameter
from .kg_retriever import KGRetriever


class CPubMedTool(Tool):
    """CPubMed医学知识图谱检索工具

    查询医学实体的相关信息，包括症状、治疗、检查、病因等
    """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.search",
            description="查询CPubMed医学知识图谱，获取疾病、药物、症状等医学实体的相关信息"
        )

        # 设置数据目录
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        """确保检索器已初始化"""
        if not self._initialized:
            print("初始化知识图谱检索器...")
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="entity",
                type="string",
                description="要查询的医学实体名称，如疾病名、药物名、症状等",
                required=True
            ),
            ToolParameter(
                name="relation",
                type="string",
                description="关系类型过滤，如'药物治疗'、'临床表现'、'病因'等，不指定则返回所有关系",
                required=False
            ),
            ToolParameter(
                name="entity_type",
                type="string",
                description="实体类型过滤，如'疾病'、'药物'、'症状'等",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回结果数量限制，默认20",
                required=False,
                default=20
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行知识图谱检索

        Args:
            parameters: 包含entity、relation、entity_type、limit参数

        Returns:
            格式化的检索结果JSON字符串
        """
        self._ensure_initialized()

        entity = parameters.get("entity")
        if not entity:
            return json.dumps({"error": "参数entity是必需的"}, ensure_ascii=False)

        relation = parameters.get("relation")
        entity_type = parameters.get("entity_type")
        limit = parameters.get("limit", 20)

        try:
            # 执行检索
            triples = self.retriever.search(
                entity=entity,
                relation_filter=relation,
                entity_type_filter=entity_type,
                limit=limit
            )

            if not triples:
                return json.dumps({
                    "entity": entity,
                    "found": False,
                    "message": f"未找到关于'{entity}'的相关信息"
                }, ensure_ascii=False, indent=2)

            # 按关系分组整理结果
            grouped_results = {}
            for triple in triples:
                rel = triple['relation']
                if rel not in grouped_results:
                    grouped_results[rel] = []

                # 判断查询实体的位置
                if triple['head_entity'] == entity:
                    grouped_results[rel].append({
                        "target": triple['tail_entity'],
                        "target_type": triple['tail_type']
                    })
                else:
                    grouped_results[rel].append({
                        "source": triple['head_entity'],
                        "source_type": triple['head_type']
                    })

            result = {
                "entity": entity,
                "found": True,
                "total_results": len(triples),
                "relations": grouped_results,
                "summary": self._generate_summary(entity, grouped_results)
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"检索失败: {str(e)}"
            }, ensure_ascii=False)

    def _generate_summary(self, entity: str, grouped_results: Dict) -> str:
        """生成检索结果摘要"""
        lines = [f"关于'{entity}'的医学知识："]

        # 优先展示的关系类型
        priority_relations = [
            "临床表现", "病因", "药物治疗", "手术治疗",
            "实验室检查", "影像学检查", "并发症", "预防"
        ]

        for rel in priority_relations:
            if rel in grouped_results:
                items = grouped_results[rel][:5]  # 每种关系最多显示5个
                items_str = "、".join([
                    item.get('target', item.get('source', ''))
                    for item in items
                ])
                lines.append(f"- {rel}: {items_str}")

        # 其他关系
        other_rels = [r for r in grouped_results.keys() if r not in priority_relations]
        if other_rels:
            lines.append(f"- 其他关系: {', '.join(other_rels[:10])}")

        return "\n".join(lines)


class CPubMedRelationTool(Tool):
    """CPubMed关系查询工具

    获取特定实体的所有关系类型和统计信息
    """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.get_relations",
            description="获取医学实体的所有关系类型和相关信息统计"
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        """确保检索器已初始化"""
        if not self._initialized:
            print("初始化知识图谱检索器...")
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="entity",
                type="string",
                description="要查询的医学实体名称",
                required=True
            ),
            ToolParameter(
                name="limit_per_relation",
                type="integer",
                description="每种关系返回的最大数量，默认10",
                required=False,
                default=10
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """获取实体的所有关系"""
        self._ensure_initialized()

        entity = parameters.get("entity")
        if not entity:
            return json.dumps({"error": "参数entity是必需的"}, ensure_ascii=False)

        limit = parameters.get("limit_per_relation", 10)

        try:
            grouped = self.retriever.get_entity_relations(entity, limit)

            if not grouped:
                return json.dumps({
                    "entity": entity,
                    "found": False,
                    "message": f"未找到关于'{entity}'的相关信息"
                }, ensure_ascii=False, indent=2)

            # 统计信息
            relation_stats = {
                rel: len(triples)
                for rel, triples in grouped.items()
            }

            result = {
                "entity": entity,
                "found": True,
                "relation_count": len(grouped),
                "relation_stats": relation_stats,
                "relations": {
                    rel: [
                        {
                            "head": t['head_entity'],
                            "head_type": t['head_type'],
                            "tail": t['tail_entity'],
                            "tail_type": t['tail_type']
                        }
                        for t in triples
                    ]
                    for rel, triples in grouped.items()
                }
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"查询失败: {str(e)}"
            }, ensure_ascii=False)
