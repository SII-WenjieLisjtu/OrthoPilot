"""CPubMed

45
"""
import json
from typing import Any, Dict, List
from pathlib import Path
import sys
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).parent.parent))

from base import Tool, ToolParameter
from .kg_retriever import KGRetriever


# 45
RELATION_TYPES = [
    "drug treatment",
    "auxiliary treatment",
    "surgical treatment",
    "radiation treatment",
    "chemotherapy",
    "prevention",
    "laboratory test",
    "imaging test",
    "auxiliary test",
    "endoscopy test",
    "histology test",
    "screening",
    "clinical manifestation",
    "etiology",
    "pathological classification",
    "complication",
    "differential diagnosis",
    "risk factor",
    "incidence",
    "affected site",
    "susceptible population",
    "onset age",
    "gender tendency",
    "endemic area",
    "seasonal prevalence",
    "mortality",
    "prognosis",
    "survival rate",
    "post-treatment symptom",
    "synonym",
    "risk assessment factor",
    "related cause",
    "related transformation",
    "related symptom",
    "department",
    "metastasis site",
    "invasion site",
    "genetic factor",
    "transmission route",
    "pathogenesis",
    "pathophysiology",
    "medical history",
    "stage",
    "comorbidity",
    "tissue invasion symptom",
]

RELATION_TRANSLATION = {
    "drug treatment": "drug_treatment",
    "auxiliary treatment": "auxiliary_treatment",
    "surgical treatment": "surgical_treatment",
    "radiation treatment": "radiation_treatment",
    "chemotherapy": "chemotherapy",
    "prevention": "prevention",
    "laboratory test": "laboratory_test",
    "imaging test": "imaging_test",
    "auxiliary test": "auxiliary_test",
    "endoscopy test": "endoscopy_test",
    "histology test": "histology_test",
    "screening": "screening",
    "clinical manifestation": "clinical_manifestation",
    "etiology": "etiology",
    "pathological classification": "pathological_classification",
    "complication": "complication",
    "differential diagnosis": "differential_diagnosis",
    "risk factor": "risk_factor",
    "incidence": "incidence",
    "affected site": "affected_site",
    "susceptible population": "susceptible_population",
    "onset age": "onset_age",
    "gender tendency": "gender_tendency",
    "endemic area": "endemic_area",
    "seasonal prevalence": "seasonal_prevalence",
    "mortality": "mortality",
    "prognosis": "prognosis",
    "survival rate": "survival_rate",
    "post-treatment symptom": "post_treatment_symptom",
    "synonym": "synonym",
    "risk assessment factor": "risk_assessment_factor",
    "related cause": "related_cause",
    "related transformation": "related_transformation",
    "related symptom": "related_symptom",
    "department": "department",
    "metastasis site": "metastasis_site",
    "invasion site": "invasion_site",
    "genetic factor": "genetic_factor",
    "transmission route": "transmission_route",
    "pathogenesis": "pathogenesis",
    "pathophysiology": "pathophysiology",
    "medical history": "medical_history",
    "stage": "stage",
    "comorbidity": "comorbidity",
    "tissue invasion symptom": "tissue_invasion_symptom",
}


class CPubMedDatabaseSummaryTool(Tool):
    """

 CPubMedstatistics
 """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.get_summary",
            description="CPubMedstatistics"
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
        return []  # not needed

    def run(self, parameters: Dict[str, Any]) -> str:
        """"""
        self._ensure_initialized()

        summary = {
            "database": "CPubMed v2.0",
            "statistics": {
                "total_triples": len(self.retriever.triples),
                "total_entities": len(self.retriever.entity_index),
                "relation_types": 45,
                "entity_types": 12
            },
            "relation_types": RELATION_TYPES,
            "entity_types": ["", "", "", "", "", "",
                           "", "", "", "", "", ""],
            "description": "CPubMedyes,, ",
            "top_relations": [
                " (689,502)", " (608,764)", " (501,590)",
                " (428,438)", " (408,257)", " (384,092)",
                " (316,224)", " (178,233)", " (138,382)",
                " (108,657)"
            ]
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)


class CPubMedGetEntityTypeTool(Tool):
    """

 specified
 """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.get_entity_type",
            description="specified(,,)"
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
                description="Search input",
                required=True
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """"""
        self._ensure_initialized()

        entity = parameters.get("entity")
        if not entity:
            return json.dumps({"error": "entity yes"}, ensure_ascii=False)

        #
        triples = self.retriever.search(entity, limit=10)

        if not triples:
            return json.dumps({
                "entity": entity,
                "found": False,
                "message": f"'{entity}'"
            }, ensure_ascii=False, indent=2)

        #
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
            "primary_type": list(entity_types)[0] if entity_types else ""
        }

        return json.dumps(result, ensure_ascii=False, indent=2)


class CPubMedFuzzySearchTool(Tool):
    """


 """

    def __init__(self, data_dir: str = None):
        super().__init__(
            name="cpubmed.fuzzy_search",
            description=", "
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
                description="Search input",
                required=True
            ),
            ToolParameter(
                name="threshold",
                type="number",
                description=", 0-1, default0.6",
                required=False,
                default=0.6
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="result, default10",
                required=False,
                default=10
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """"""
        self._ensure_initialized()

        keyword = parameters.get("keyword")
        if not keyword:
            return json.dumps({"error": "keyword is required"}, ensure_ascii=False)

        threshold = parameters.get("threshold", 0.6)
        limit = parameters.get("limit", 10)

        #
        keyword_lower = keyword.lower()
        matches = []

        for entity in self.retriever.entity_index.keys():
            entity_lower = entity.lower()

            #
            if keyword_lower in entity_lower:
                #,
                similarity = 0.8 + (len(keyword_lower) / len(entity_lower)) * 0.2
            else:
                #
                similarity = SequenceMatcher(None, keyword_lower, entity_lower).ratio()

            if similarity >= threshold:
                matches.append({
                    "entity": entity,
                    "similarity": round(similarity, 3)
                })

        #
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        matches = matches[:limit]

        #
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
                match['type'] = ""

        result = {
            "keyword": keyword,
            "threshold": threshold,
            "total_matches": len(matches),
            "matches": matches
        }

        return json.dumps(result, ensure_ascii=False, indent=2)


def create_relation_tool_class(relation_name: str):
    """

 Args:
 relation_name: ()

 Returns:

 """
    #
    tool_suffix = RELATION_TRANSLATION.get(relation_name, relation_name)

    class RelationSpecificTool(Tool):
        """(generate)"""

        def __init__(self, data_dir: str = None):
            super().__init__(
                name=f"cpubmed.query_{tool_suffix}",
                description=f"'{relation_name}'"
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
                    description=f"{self.relation_name}",
                    required=True
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="result, default20",
                    required=False,
                    default=20
                )
            ]

        def run(self, parameters: Dict[str, Any]) -> str:
            """"""
            self._ensure_initialized()

            entity = parameters.get("entity")
            if not entity:
                return json.dumps({"error": "entity yes"}, ensure_ascii=False)

            limit = parameters.get("limit", 20)

            # relation
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
                    "message": f"'{entity}''{self.relation_name}'"
                }, ensure_ascii=False, indent=2)

            # result
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

    #
    RelationSpecificTool.__name__ = f"CPubMed{tool_suffix}Tool"

    return RelationSpecificTool


# generate45
RELATION_TOOL_CLASSES = {
    relation: create_relation_tool_class(relation)
    for relation in RELATION_TYPES
}
