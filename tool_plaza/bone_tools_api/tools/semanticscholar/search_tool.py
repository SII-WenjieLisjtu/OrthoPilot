"""Semantic Scholar Paper Search Tool"""
import os
import json
from typing import Any, Dict, List

import requests

from tools.base import Tool, ToolParameter


class SemanticScholarSearchTool(Tool):
    """Semantic Scholar论文搜索工具

    使用Semantic Scholar API搜索学术论文
    """

    def __init__(self):
        super().__init__(
            name="semanticscholar.search",
            description="搜索Semantic Scholar学术论文数据库，返回论文标题、作者、年份、摘要和URL等信息"
        )

        # 从环境变量获取API key
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.base_url = "https://YOUR_SEMANTIC_SCHOLAR_API_URL"

    def get_parameters(self) -> List[ToolParameter]:
        """返回工具参数定义"""
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询关键词，例如：'machine learning'、'deep learning'等",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回结果数量限制，默认为10，最大100",
                required=False,
                default=10
            ),
            ToolParameter(
                name="fields",
                type="string",
                description="返回字段，逗号分隔，默认为'title,authors,year,abstract,url'",
                required=False,
                default="title,authors,year,abstract,url"
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行论文搜索

        Args:
            parameters: 包含query、limit、fields的字典

        Returns:
            JSON格式的搜索结果字符串
        """
        query = parameters.get("query")
        if not query:
            raise ValueError("参数'query'是必需的")

        limit = parameters.get("limit", 10)
        fields = parameters.get("fields", "title,authors,year,abstract,url")

        # 验证limit范围
        try:
            limit = int(limit)
            if limit < 1:
                limit = 1
            elif limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 10

        # 构建请求
        headers = {
            "x-api-key": self.api_key
        }

        params = {
            "query": query,
            "limit": limit,
            "fields": fields
        }

        try:
            # 发送请求
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            # 解析响应
            data = response.json()

            # 构建结果
            result = {
                "query": query,
                "total_results": data.get("total", 0),
                "returned_count": len(data.get("data", [])),
                "papers": []
            }

            # 处理论文数据
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
            raise Exception("请求超时：Semantic Scholar API响应时间过长")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP错误：{e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败：{str(e)}")
        except json.JSONDecodeError:
            raise Exception("API返回的数据格式错误，无法解析JSON")
        except Exception as e:
            raise Exception(f"搜索论文时发生错误：{str(e)}")
