#!/usr/bin/env python3
"""
medical_trajectory_generator.py - generate

:
 - Fathom-DeepResearch ReCall trajectory generation
 - (5)
 - generate
 - output the OrthoPilot trajectory JSON schema

:
 python medical_trajectory_generator.py \
 --question "patient,result" \
 --model-url http://localhost:8000 \
 --executors http://localhost:8000 \
 --tokenizer FractalAIResearch/Fathom-Search-4B \
 --output-path./output/trajectory.json \
 --max-searches 5
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Import the medical ReCall agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents', 'inference'))
from re_call_medical import ReCallMedical

# Optional: HF tokenizer
try:
    from transformers import AutoTokenizer
except Exception:
    AutoTokenizer = None


# Medical domain tool schemas
MEDICAL_ENV = "from ehr_api import get_patient, get_lab_results, search_guidelines"

MEDICAL_SCHEMAS: List[Dict[str, Any]] = [
    # {
    # "name": "get_patient",
    # "description": "patient(,,,,)",
    # "parameters": {
    # "type": "object",
    # "properties": {},
    # "required": [],
    # },
    # },
    {
        "name": "search_guidelines",
        "description": "Search public clinical guidelines or web sources for a focused query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "domain": {"type": "string", "description": "Optional source domain or guideline scope"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_differential_diagnosis",
        "description": "Search for differential diagnoses based on symptoms and context.",
        "parameters": {
            "type": "object",
            "properties": {
                "symptoms": {"type": "array", "items": {"type": "string"}, "description": "Symptoms or clinical findings"},
                "age": {"type": "integer", "description": "Patient age"},
                "specialty": {"type": "string", "description": "Optional clinical specialty"},
            },
            "required": ["symptoms"],
        },
    },
    {
        "name": "kg_search",
        "description": "Search the medical knowledge graph for entities and optional relations.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": "Medical entity to search for",
                },
                "relation": {
                    "type": "string",
                    "description": "Optional relation filter. If omitted, the search returns the most relevant relations.",
                },
            },
            "required": ["entity"],
        },
    },
    {
        "name": "kg_get_relations",
        "description": "List available knowledge-graph relations for a medical entity.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Medical entity"},
                "limit_per_relation": {"type": "integer", "description": "Maximum results per relation"},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "kg_fuzzy_search",
        "description": "Fuzzy-search medical knowledge-graph entities by keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Keyword or partial entity name",
                },
                "threshold": {
                    "type": "number",
                    "description": "Similarity threshold between 0 and 1",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "medibook_search",
        "description": "Search medical-book content for background knowledge.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_mode": {
                    "type": "string",
                    "description": "Search mode, such as embedding or keyword",
                },
                "query": {
                    "type": "string",
                    "description": "Medical-book search query",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "semanticscholar_search",
        "description": "Search Semantic Scholar for biomedical literature.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Literature search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of papers to return",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "wikipedia_search",
        "description": "Search Wikipedia for concise background context.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Question or topic to search",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "pubmed_search",
        "description": "Search PubMed for biomedical evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Biomedical question or search query",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "books_search",
        "description": "Search textbook-style medical references.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Clinical topic or question",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "statpearls_search",
        "description": "Search StatPearls for clinical summaries.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Clinical topic or question",
                },
            },
            "required": ["question"],
        },
    }


]


def format_trajectory_for_output(trajectory: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
 Format trajectory for JSON output compatible with the OrthoPilot trajectory format.
 Converts internal format to the expected output format.
 """
    formatted = []
    for step in trajectory:
        role = step.get("role", "")
        content = step.get("content", "")

        # Clean up content - extract key parts
        if role == "gpt":
            # For GPT responses, we want to keep think, tool_call, and answer tags
            formatted.append({
                "role": role,
                "content": content
            })
        elif role == "user":
            # For user messages, keep tool_response tags
            formatted.append({
                "role": role,
                "content": content
            })
        elif role == "system":
            # Keep system messages as is
            formatted.append({
                "role": role,
                "content": content
            })

    return formatted


def main():
    parser = argparse.ArgumentParser(
        description="Generate a medical search trajectory"
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Clinical question or task prompt"
    )
    parser.add_argument(
        "--model-url",
        required=True,
        help="Model endpoint URL"
    )
    parser.add_argument(
        "--executors",
        required=True,
        help="Executor service URL"
    )
    parser.add_argument(
        "--tokenizer",
        default="FractalAIResearch/Fathom-Search-4B",
        help="Hugging Face tokenizer name or path"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="Generation temperature"
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=40960,
        help="Maximum generated tokens"
    )
    parser.add_argument(
        "--max-searches",
        type=int,
        default=5,
        help="Maximum search tool calls"
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--patient-id",
        default="unknown",
        help="patientID(file)"
    )

    args = parser.parse_args()

    # Initialize tokenizer
    tok = None
    if args.tokenizer:
        if AutoTokenizer is None:
            raise RuntimeError("transformers not installed; `pip install transformers`")
        print(f"Loading tokenizer: {args.tokenizer}")
        tok = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True)

    # Initialize medical agent with search limit
    print(f"Initializing medical agent with max {args.max_searches} searches...")
    agent = ReCallMedical(
        executor_url=args.executors.strip(),
        max_searches=args.max_searches
    )

    # Run the agent
    print(f"Running agent on question: {args.question}")
    print("="*80)

    transcript, tool_calls, trajectory = agent.run(
        env=MEDICAL_ENV,
        func_schemas=json.dumps(MEDICAL_SCHEMAS, ensure_ascii=False, indent=2),
        question=args.question,
        model_url=args.model_url,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        tokenizer=tok,
    )

    print("="*80)
    print(f"Agent completed. Total tool calls: {len(tool_calls)}")
    print(f"Search calls made: {agent.search_count}/{args.max_searches}")

    # Format trajectory for output
    formatted_trajectory = format_trajectory_for_output(trajectory)

    # Prepare output
    output_data = formatted_trajectory

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output_path) if os.path.dirname(args.output_path) else ".", exist_ok=True)

    # Write trajectory to file
    with open(args.output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nTrajectory saved to: {args.output_path}")
    print(f"Total steps in trajectory: {len(formatted_trajectory)}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Question: {args.question}")
    print(f"Total interactions: {len(trajectory)}")
    print(f"Tool calls made: {len(tool_calls)}")
    print(f"Search calls: {agent.search_count}/{args.max_searches}")
    print(f"Output saved to: {args.output_path}")


if __name__ == "__main__":
    main()
