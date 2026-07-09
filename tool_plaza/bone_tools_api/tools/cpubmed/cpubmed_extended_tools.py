"""CPubMed扩展工具集

包含45个关系类型的专用查询工具和其他实用工具
"""
import json
from typing import Any, Dict, List
from pathlib import Path
import sys
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).parent.parent))

from base import Tool, ToolParameter
from .kg_retriever import KGRetriever


# 45种关系类型定义
RELATION_TYPES = [
    "药物治疗", "辅助治疗", "手术治疗", "放射治疗", "化疗", "预防",
    "实验室检查", "影像学检查", "辅助检查", "内窥镜检查", "组织学检查", "筛查",
    "临床表现", "病因", "病理分型", "并发症", "鉴别诊断", "高危因素",
    "发病率", "发病部位", "多发群体", "发病年龄", "发病性别倾向", "多发地区", "多发季节", "死亡率",
    "预后状况", "预后生存率", "治疗后症状",
    "同义词", "风险评估因素", "相关（导致）", "相关（转化）", "相关（症状）",
    "就诊科室", "转移部位", "外侵部位", "遗传因素", "传播途径",
    "发病机制", "病理生理", "病史", "阶段", "合并症", "侵及周围组织转移的症状"
]

# 中英文关系类型翻译表
RELATION_TRANSLATION = {
    "药物治疗": "drug_treatment",
    "辅助治疗": "auxiliary_treatment",
    "手术治疗": "surgical_treatment",
    "放射治疗": "radiation_treatment",
    "化疗": "chemotherapy",
    "预防": "prevention",
    "实验室检查": "laboratory_test",
    "影像学检查": "imaging_test",
    "辅助检查": "auxiliary_test",
    "内窥镜检查": "endoscopy_test",
    "组织学检查": "histology_test",
    "筛查": "screening",
    "临床表现": "clinical_manifestation",
    "病因": "etiology",
    "病理分型": "pathological_classification",
    "并发症": "complication",
    "鉴别诊断": "differential_diagnosis",
    "高危因素": "risk_factor",
    "发病率": "incidence",
    "发病部位": "affected_site",
    "多发群体": "susceptible_population",
    "发病年龄": "onset_age",
    "发病性别倾向": "gender_tendency",
    "多发地区": "endemic_area",
    "多发季节": "seasonal_prevalence",
    "死亡率": "mortality",
    "预后状况": "prognosis",
    "预后生存率": "survival_rate",
    "治疗后症状": "post_treatment_symptom",
    "同义词": "synonym",
    "风险评估因素": "risk_assessment_factor",
    "相关（导致）": "related_cause",
    "相关（转化）": "related_transformation",
    "相关（症状）": "related_symptom",
    "就诊科室": "department",
    "转移部位": "metastasis_site",
    "外侵部位": "invasion_site",
    "遗传因素": "genetic_factor",
    "传播途径": "transmission_route",
    "发病机制": "pathogenesis",
    "病理生理": "pathophysiology",
    "病史": "medical_history",
    "阶段": "stage",
    "合并症": "comorbidity",
    "侵及周围组织转移的症状": "tissue_invasion_symptom"
}


class CPubMedDatabaseSummaryTool(Tool):
    """数据库概览工具

    返回CPubMed知识图谱的统计信息和概览
    """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.get_summary",
            description="获取CPubMed医学知识图谱的统计信息和数据概览"
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return []  # 无需参数

    def run(self, parameters: Dict[str, Any]) -> str:
        """返回数据库概览"""
        self._ensure_initialized()

        summary = {
            "database": "CPubMed医学知识图谱 v2.0",
            "statistics": {
                "total_triples": len(self.retriever.triples),
                "total_entities": len(self.retriever.entity_index),
                "relation_types": 45,
                "entity_types": 12
            },
            "relation_types": RELATION_TYPES,
            "entity_types": ["疾病", "检查", "药物", "其他治疗", "手术治疗", "症状",
                           "社会学", "流行病学", "部位", "其他", "预后", "未知类型"],
            "description": "CPubMed是一个大规模的中文医学知识图谱，包含医学实体、关系和相关属性信息",
            "top_relations": [
                "药物治疗 (689,502)", "辅助治疗 (608,764)", "实验室检查 (501,590)",
                "同义词 (428,438)", "手术治疗 (408,257)", "临床表现 (384,092)",
                "影像学检查 (316,224)", "病因 (178,233)", "病理分型 (138,382)",
                "并发症 (108,657)"
            ]
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)


class CPubMedGetEntityTypeTool(Tool):
    """获取实体类型工具

    查询指定关键词对应的实体类型
    """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.get_entity_type",
            description="获取指定医学实体的类型信息（疾病、药物、症状等）"
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="entity",
                type="string",
                description="要查询类型的实体名称",
                required=True
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """查询实体类型"""
        self._ensure_initialized()

        entity = parameters.get("entity")
        if not entity:
            return json.dumps({"error": "参数entity是必需的"}, ensure_ascii=False)

        # 查询实体的三元组
        triples = self.retriever.search(entity, limit=10)

        if not triples:
            return json.dumps({
                "entity": entity,
                "found": False,
                "message": f"未找到实体'{entity}'"
            }, ensure_ascii=False, indent=2)

        # 收集实体类型
        entity_types = set()
        for triple in triples:
            if triple['head_entity'] == entity:
                entity_types.add(triple['head_type'])
            if triple['tail_entity'] == entity:
                entity_types.add(triple['tail_type'])

        result = {
            "entity": entity,
            "found": True,
            "types": list(entity_types),
            "primary_type": list(entity_types)[0] if entity_types else "未知"
        }

        return json.dumps(result, ensure_ascii=False, indent=2)


class CPubMedFuzzySearchTool(Tool):
    """模糊搜索工具

    在知识图谱中搜索与关键词相似的实体
    """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.fuzzy_search",
            description="在知识图谱中模糊搜索实体，支持相似度匹配"
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="keyword",
                type="string",
                description="要搜索的关键词",
                required=True
            ),
            ToolParameter(
                name="threshold",
                type="number",
                description="相似度阈值，0-1之间，默认0.6",
                required=False,
                default=0.6
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回结果数量限制，默认10",
                required=False,
                default=10
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行模糊搜索"""
        self._ensure_initialized()

        keyword = parameters.get("keyword")
        if not keyword:
            return json.dumps({"error": "参数keyword是必需的"}, ensure_ascii=False)

        threshold = parameters.get("threshold", 0.6)
        limit = parameters.get("limit", 10)

        # 搜索相似实体
        keyword_lower = keyword.lower()
        matches = []

        for entity in self.retriever.entity_index.keys():
            entity_lower = entity.lower()

            # 计算相似度
            if keyword_lower in entity_lower:
                # 包含关键词，相似度较高
                similarity = 0.8 + (len(keyword_lower) / len(entity_lower)) * 0.2
            else:
                # 使用序列匹配器计算相似度
                similarity = SequenceMatcher(None, keyword_lower, entity_lower).ratio()

            if similarity >= threshold:
                matches.append({
                    "entity": entity,
                    "similarity": round(similarity, 3)
                })

        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        matches = matches[:limit]

        # 为每个匹配的实体获取类型
        for match in matches:
            entity = match['entity']
            triples = self.retriever.search(entity, limit=1)
            if triples:
                triple = triples[0]
                if triple['head_entity'] == entity:
                    match['type'] = triple['head_type']
                else:
                    match['type'] = triple['tail_type']
            else:
                match['type'] = "未知"

        result = {
            "keyword": keyword,
            "threshold": threshold,
            "total_matches": len(matches),
            "matches": matches
        }

        return json.dumps(result, ensure_ascii=False, indent=2)


def create_relation_tool_class(relation_name: str):
    """动态创建关系类型专用工具类

    Args:
        relation_name: 关系类型名称（中文）

    Returns:
        工具类
    """
    # 使用英文名称作为工具后缀
    tool_suffix = RELATION_TRANSLATION.get(relation_name, relation_name)

    class RelationSpecificTool(Tool):
        """关系特定查询工具（动态生成）"""

        def __init__(self, data_dir: str = None):
            super().__init__(
                name=f"cpubmed.query_{tool_suffix}",
                description=f"查询医学实体的'{relation_name}'相关信息"
            )

            self.relation_name = relation_name

            if data_dir is None:
                data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

            self.retriever = KGRetriever(str(data_dir))
            self._initialized = False

        def _ensure_initialized(self):
            if not self._initialized:
                self.retriever.build_index()
                self._initialized = True

        def get_parameters(self) -> List[ToolParameter]:
            return [
                ToolParameter(
                    name="entity",
                    type="string",
                    description=f"要查询{self.relation_name}的医学实体名称",
                    required=True
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
            """执行关系特定查询"""
            self._ensure_initialized()

            entity = parameters.get("entity")
            if not entity:
                return json.dumps({"error": "参数entity是必需的"}, ensure_ascii=False)

            limit = parameters.get("limit", 20)

            # 使用固定的relation进行查询
            triples = self.retriever.search(
                entity=entity,
                relation_filter=self.relation_name,
                limit=limit
            )

            if not triples:
                return json.dumps({
                    "entity": entity,
                    "relation": self.relation_name,
                    "found": False,
                    "message": f"未找到关于'{entity}'的'{self.relation_name}'信息"
                }, ensure_ascii=False, indent=2)

            # 整理结果
            results = []
            for triple in triples:
                if triple['head_entity'] == entity:
                    results.append({
                        "target": triple['tail_entity'],
                        "target_type": triple['tail_type']
                    })
                else:
                    results.append({
                        "source": triple['head_entity'],
                        "source_type": triple['head_type']
                    })

            result = {
                "entity": entity,
                "relation": self.relation_name,
                "found": True,
                "total_results": len(results),
                "results": results
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

    # 设置类名
    RelationSpecificTool.__name__ = f"CPubMed{tool_suffix}Tool"

    return RelationSpecificTool


# 生成45个关系类型工具类
RELATION_TOOL_CLASSES = {
    relation: create_relation_tool_class(relation)
    for relation in RELATION_TYPES
}
