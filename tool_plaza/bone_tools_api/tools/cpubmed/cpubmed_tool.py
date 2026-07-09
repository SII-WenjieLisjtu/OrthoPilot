"""CPubMed

model
"""
import os
import json
from typing import Any, Dict, List
from pathlib import Path
import sys

# path
sys.path.append(str(Path(__file__).parent.parent))

from base import Tool, ToolParameter
from .kg_retriever import KGRetriever


class CPubMedTool(Tool):
    """CPubMed

,,,,
 """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.search",
            description="CPubMed,,, "
        )

        #
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        """Build the retrieval index on first use."""
        if not self._initialized:
            print("Building C-PubMed index...")
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="entity",
                type="string",
                description="Biomedical entity to search for",
                required=True
            ),
            ToolParameter(
                name="relation",
                type="string",
                description="Optional relation filter",
                required=False
            ),
            ToolParameter(
                name="entity_type",
                type="string",
                description="Optional entity type filter",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results; defaults to 20",
                required=False,
                default=20
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """

 Args:
 parameters: entity, relation, entity_type, limit

 Returns:
 resultJSON
 """
        self._ensure_initialized()

        entity = parameters.get("entity")
        if not entity:
            return json.dumps({"error": "entity yes"}, ensure_ascii=False)

        relation = parameters.get("relation")
        entity_type = parameters.get("entity_type")
        limit = parameters.get("limit", 20)

        try:
            #
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
                    "message": f"'{entity}'"
                }, ensure_ascii=False, indent=2)

            # result
            grouped_results = {}
            for triple in triples:
                rel = triple['relation']
                if rel not in grouped_results:
                    grouped_results[rel] = []

                # judgement
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
                "error": f": {str(e)}"
            }, ensure_ascii=False)

    def _generate_summary(self, entity: str, grouped_results: Dict) -> str:
        """generateresult"""
        lines = [f"'{entity}': "]

        #
        priority_relations = [
            "", "", "", "",
            "", "", "", ""
        ]

        for rel in priority_relations:
            if rel in grouped_results:
                items = grouped_results[rel][:5]  # 5
                items_str = ", ".join([
                    item.get('target', item.get('source', ''))
                    for item in items
                ])
                lines.append(f"- {rel}: {items_str}")

        #
        other_rels = [r for r in grouped_results.keys() if r not in priority_relations]
        if other_rels:
            lines.append(f"-: {', '.join(other_rels[:10])}")

        return "\n".join(lines)


class CPubMedRelationTool(Tool):
    """CPubMed

 statistics
 """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.get_relations",
            description="statistics"
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "cpubmed"

        self.retriever = KGRetriever(str(data_dir))
        self._initialized = False

    def _ensure_initialized(self):
        """Build the retrieval index on first use."""
        if not self._initialized:
            print("Building C-PubMed index...")
            self.retriever.build_index()
            self._initialized = True

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="entity",
                type="string",
                description="Search input",
                required=True
            ),
            ToolParameter(
                name="limit_per_relation",
                type="integer",
                description=", default10",
                required=False,
                default=10
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """"""
        self._ensure_initialized()

        entity = parameters.get("entity")
        if not entity:
            return json.dumps({"error": "entity yes"}, ensure_ascii=False)

        limit = parameters.get("limit_per_relation", 10)

        try:
            grouped = self.retriever.get_entity_relations(entity, limit)

            if not grouped:
                return json.dumps({
                    "entity": entity,
                    "found": False,
                    "message": f"'{entity}'"
                }, ensure_ascii=False, indent=2)

            # statistics
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
                "error": f": {str(e)}"
            }, ensure_ascii=False)
