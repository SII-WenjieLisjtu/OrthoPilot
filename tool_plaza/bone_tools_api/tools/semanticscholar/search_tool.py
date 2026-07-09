"""Semantic Scholar Paper Search Tool"""
import os
import json
from typing import Any, Dict, List

import requests

from tools.base import Tool, ToolParameter


class SemanticScholarSearchTool(Tool):
    """Semantic Scholar

 Semantic Scholar API
 """

    def __init__(self):
        super().__init__(
            name="semanticscholar.search",
            description="Semantic Scholar,,,, URL"
        )

        # API key
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def get_parameters(self) -> List[ToolParameter]:
        """"""
        return [
            ToolParameter(
                name="query",
                type="string",
                description=",: 'machine learning', 'deep learning'",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="result, default10, 100",
                required=False,
                default=10
            ),
            ToolParameter(
                name="fields",
                type="string",
                description=",, default'title,authors,year,abstract,url'",
                required=False,
                default="title,authors,year,abstract,url"
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """

 Args:
 parameters: query, limit, fields

 Returns:
 JSONresult
 """
        query = parameters.get("query")
        if not query:
            raise ValueError("'query'yes")

        limit = parameters.get("limit", 10)
        fields = parameters.get("fields", "title,authors,year,abstract,url")

        # limit
        try:
            limit = int(limit)
            if limit < 1:
                limit = 1
            elif limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 10

        #
        headers = {
            "x-api-key": self.api_key
        }

        params = {
            "query": query,
            "limit": limit,
            "fields": fields
        }

        try:
            #
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            #
            data = response.json()

            # result
            result = {
                "query": query,
                "total_results": data.get("total", 0),
                "returned_count": len(data.get("data", [])),
                "papers": []
            }

            #
            for paper in data.get("data", []):
                paper_info = {
                    "paperId": paper.get("paperId"),
                    "title": paper.get("title"),
                    "year": paper.get("year"),
                    "abstract": paper.get("abstract"),
                    "url": paper.get("url"),
                    "authors": [
                        author.get("name")
                        for author in paper.get("authors", [])
                    ] if paper.get("authors") else []
                }
                result["papers"].append(paper_info)

            return json.dumps(result, ensure_ascii=False, indent=2)

        except requests.exceptions.Timeout:
            raise Exception(": Semantic Scholar API")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTPerror: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f": {str(e)}")
        except json.JSONDecodeError:
            raise Exception("APIerror, JSON")
        except Exception as e:
            raise Exception(f"error: {str(e)}")
