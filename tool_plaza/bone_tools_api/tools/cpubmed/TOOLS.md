# CPubMed Tools

This directory documents CPubMed knowledge graph tools for the Tool Plaza API server. These tools are registered only when local CPubMed data files are supplied under `tool_plaza/bone_tools_api/tools/data/cpubmed/`. In the default public release, the data files are excluded and the API server skips these tools.

## Core tools

### `cpubmed.search`

General knowledge graph query.

Parameters:

- `entity` (required): medical entity name.
- `relation` (optional): relation type filter.
- `entity_type` (optional): entity type filter.
- `limit` (optional): maximum number of returned records.

Example:

```python
response = tool.execute({
 "entity": "diabetes",
 "relation": "drug treatment",
 "limit": 10,
})
```

### `cpubmed.get_relations`

Returns relation types and summary records for a given entity.

Parameters:

- `entity` (required): medical entity name.
- `limit_per_relation` (optional): maximum records per relation.

## Utility tools

- `cpubmed.get_summary`: database summary and relation statistics.
- `cpubmed.get_entity_type`: entity type lookup.
- `cpubmed.fuzzy_search`: fuzzy entity search.

## Relation-specific tools

The API also includes relation-specific wrappers named `cpubmed.query_<relation_name>`. They call the same underlying CPubMed retriever with a fixed relation filter.

Examples:

- `cpubmed.query_drug_treatment`
- `cpubmed.query_clinical_manifestation`
- `cpubmed.query_complication`
- `cpubmed.query_imaging_test`

Use `GET /tools` on the running API server to inspect the current complete list and schemas.
