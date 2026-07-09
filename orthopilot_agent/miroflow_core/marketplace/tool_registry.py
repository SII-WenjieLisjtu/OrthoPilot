"""
工具注册表 - 管理所有可用工具的元数据
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ToolMetadata:
    """工具元数据"""
    id: str
    name_en: str
    name_zh: str
    category: str  # internal | external
    description_en: str
    description_zh: str
    server_name: str
    config_file: str
    enabled: bool = False
    icon: str = "🔧"
    version: str = "1.0.0"
    author: str = "MiroFlow Team"
    tools: List[Dict] = field(default_factory=list)

    def dict(self, lang: str = "en"):
        """转换为字典"""
        use_zh = (lang or "en").lower() == "zh"
        return {
            "id": self.id,
            "name": self.name_zh if use_zh else self.name_en,
            "category": self.category,
            "description": self.description_zh if use_zh else self.description_en,
            "server_name": self.server_name,
            "config_file": self.config_file,
            "enabled": self.enabled,
            "icon": self.icon,
            "version": self.version,
            "author": self.author,
            "tools": self.tools,
        }


class ToolRegistry:
    """管理所有可用工具的注册表"""

    def __init__(self, config_dir: Path = None):
        self.tools: Dict[str, ToolMetadata] = {}
        self.config_dir = config_dir or Path("config/tool")
        self._load_tools_from_config()

    def _load_tools_from_config(self):
        """从配置目录加载工具元数据"""
        # 预定义的工具元数据（基于现有的 MCP servers）
        predefined_tools = [
            ToolMetadata(
                id="tool-ehr",
                name_en="Electronic Health Records",
                name_zh="电子病历系统",
                category="internal",
                description_en="Query patient electronic health record information",
                description_zh="查询患者电子病历信息",
                server_name="ehr_mcp_server",
                config_file="config/tool/tool-ehr.yaml",
                icon="🏥",
            ),
            ToolMetadata(
                id="tool-similar-case",
                name_en="Similar Case Retrieval",
                name_zh="相似病例检索",
                category="internal",
                description_en="Retrieve similar case information",
                description_zh="检索相似病例信息",
                server_name="similar_case_mcp_server",
                config_file="config/tool/tool-similar-case.yaml",
                icon="📋",
            ),
            ToolMetadata(
                id="tool-knowledge-graph",
                name_en="Medical Knowledge Graph",
                name_zh="医学知识图谱",
                category="external",
                description_en="Query the medical knowledge graph",
                description_zh="查询医学知识图谱",
                server_name="knowledge_graph_mcp_server",
                config_file="config/tool/tool-knowledge-graph.yaml",
                icon="🧠",
            ),
            ToolMetadata(
                id="tool-medrag",
                name_en="Medical Literature Retrieval",
                name_zh="医学文献检索",
                category="external",
                description_en="Search medical literature and research",
                description_zh="检索医学文献和研究",
                server_name="medrag_mcp_server",
                config_file="config/tool/tool-medrag.yaml",
                icon="📚",
                version="2.0.0",
            ),
            ToolMetadata(
                id="tool-web-search",
                name_en="Web Search",
                name_zh="网页搜索",
                category="external",
                description_en="Search internet information",
                description_zh="搜索互联网信息",
                server_name="searching_mcp_server",
                config_file="config/tool/tool-web-search.yaml",
                icon="🔍",
            ),
            ToolMetadata(
                id="tool-vision",
                name_en="Medical Imaging Analysis",
                name_zh="医学影像分析",
                category="internal",
                description_en="Analyze medical images such as X-ray, CT, and MRI",
                description_zh="分析医学影像（X光、CT、MRI等）",
                server_name="vision_mcp_server",
                config_file="config/tool/tool-vision.yaml",
                icon="👁️",
            ),
        ]

        for tool in predefined_tools:
            self.tools[tool.id] = tool
            print(f"Registered tool: {tool.name_en} ({tool.id})")

    def _normalize_category(self, category: Optional[str]) -> Optional[str]:
        if category in {None, ""}:
            return None
        if category == "院内信息":
            return "internal"
        if category == "院外知识":
            return "external"
        return category

    def list_tools(self, category: Optional[str] = None) -> List[ToolMetadata]:
        """列出所有工具"""
        normalized_category = self._normalize_category(category)
        tools = list(self.tools.values())
        if normalized_category:
            tools = [t for t in tools if t.category == normalized_category]
        return tools

    def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """获取工具详情"""
        return self.tools.get(tool_id)

    def register_tool(self, tool_metadata: ToolMetadata):
        """注册新工具"""
        self.tools[tool_metadata.id] = tool_metadata
        print(f"Registered tool: {tool_metadata.name_en} ({tool_metadata.id})")
