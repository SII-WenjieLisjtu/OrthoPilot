"""Tool Call API Server

API,
"""
import asyncio
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# load
# load.env file, does not existload.openai file()
env_file = Path(__file__).parent / ".env"
openai_file = Path(__file__).parent / ".openai"

if env_file.exists():
    load_dotenv(env_file)
elif openai_file.exists():
    load_dotenv(openai_file)

from tools.base import Tool
from tools.base.echo_tool import EchoTool
from tools.cpubmed import (
    CPubMedTool,
    CPubMedRelationTool,
    CPubMedDatabaseSummaryTool,
    CPubMedGetEntityTypeTool,
    CPubMedFuzzySearchTool,
    RELATION_TOOL_CLASSES,
    RELATION_TYPES,
    RELATION_TRANSLATION
)
from tools.medibook import MedicalBookTool
from tools.semanticscholar import SemanticScholarSearchTool
from logger_config import server_logger as logger, tool_logger, truncate_text


# ============= model =============
class ToolExecuteRequest(BaseModel):
    """Request body for executing a registered tool."""
    tool_name: str = Field(..., description="Tool name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class ToolExecuteResponse(BaseModel):
    """Response body returned after tool execution."""
    success: bool = Field(..., description="Whether execution succeeded")
    tool_name: str = Field(..., description="Tool name")
    data: Any = Field(None, description="Tool result payload")
    error: Optional[str] = Field(None, description="Error message, if any")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: str = Field(..., description="Response timestamp")


class ToolListResponse(BaseModel):
    """Response body listing available tools."""
    total_tools: int = Field(..., description="Total number of tools")
    categories: Dict[str, int] = Field(..., description="Tool count by category")
    tools: List[str] = Field(..., description="Available tool names")


# ============= Main =============
class ToolRegistry:
    """"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.executor = ThreadPoolExecutor(max_workers=50)  # CPU-bound tasks
        self._initialize_tools()

    def _initialize_tools(self):
        """"""
        logger.info("...")

        try:
            #
            logger.info("...")
            self.register_tool(EchoTool())

            # CPubMed
            logger.info("CPubMed...")
            self.register_tool(CPubMedTool())
            self.register_tool(CPubMedRelationTool())

            # CPubMed
            logger.info("CPubMed...")
            self.register_tool(CPubMedDatabaseSummaryTool())
            self.register_tool(CPubMedGetEntityTypeTool())
            self.register_tool(CPubMedFuzzySearchTool())

            # CPubMed
            logger.info("CPubMed(45)...")
            for relation_name, tool_class in RELATION_TOOL_CLASSES.items():
                try:
                    tool = tool_class()
                    self.register_tool(tool)
                except Exception as e:
                    logger.error(f" {relation_name}: {e}")

            logger.info("Loading MedicalBook...")
            try:
                self.register_tool(MedicalBookTool())
            except FileNotFoundError as e:
                logger.warning(f"MedicalBook data is not included in this public release: {e}")

            # Semantic Scholar
            logger.info("Semantic Scholar...")
            self.register_tool(SemanticScholarSearchTool())

            logger.info(f", {len(self.tools)} ")

        except Exception as e:
            logger.error(f": {e}", exc_info=True)
            raise

    def register_tool(self, tool: Tool):
        """"""
        self.tools[tool.name] = tool
        logger.debug(f": {tool.name}")

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """"""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """"""
        return list(self.tools.keys())

    async def execute_tool_async(self, tool_name: str, parameters: Dict[str, Any]) -> ToolExecuteResponse:
        """"""
        start_time = time.time()

        #,
        params_str = truncate_text(str(parameters), 200)
        tool_logger.info(f": {tool_name},: {params_str}")

        tool = self.get_tool(tool_name)
        if not tool:
            tool_logger.error(f"does not exist: {tool_name}")
            return ToolExecuteResponse(
                success=False,
                tool_name=tool_name,
                error=f" '{tool_name}' does not exist",
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )

        try:
            # ()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                tool.execute,
                parameters
            )

            execution_time = time.time() - start_time

            # result,
            if response.success:
                data_preview = truncate_text(str(response.data), 300)
                tool_logger.info(f": {tool_name},: {execution_time:.3f}s,: {data_preview}")
            else:
                tool_logger.warning(f": {tool_name},: {execution_time:.3f}s, error: {response.error}")

            return ToolExecuteResponse(
                success=response.success,
                tool_name=tool_name,
                data=response.data if response.success else None,
                error=response.error if not response.success else None,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f": {str(e)}"
            tool_logger.error(f"{error_msg}", exc_info=True)

            return ToolExecuteResponse(
                success=False,
                tool_name=tool_name,
                error=error_msg,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )


# ============= FastAPI =============
app = FastAPI(
    title="Tool Call API Server",
    description="API",
    version="0.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#
tool_registry = None


@app.on_event("startup")
async def startup_event():
    """"""
    global tool_registry
    logger.info("=" * 80)
    logger.info("Tool Call API Server...")
    logger.info("=" * 80)

    try:
        tool_registry = ToolRegistry()
        logger.info("!")
        logger.info(f": {len(tool_registry.tools)}")
        logger.info(f"API: http://localhost:8000")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f": {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """"""
    logger.info("Tool Call API Server...")
    if tool_registry:
        tool_registry.executor.shutdown(wait=True)
    logger.info("")


# ============= API =============

@app.get("/", tags=["service"])
async def root():
    """path"""
    logger.debug("Root endpoint requested")
    return {
        "service": "Tool Call API Server",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "total_tools": len(tool_registry.tools) if tool_registry else 0
    }


@app.get("/health", tags=["health"])
async def health_check():
    """"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tools_loaded": len(tool_registry.tools) if tool_registry else 0
    }


@app.get("/tools", response_model=ToolListResponse, tags=["tools"])
async def list_tools():
    """"""
    logger.info("Tool list requested")

    tools = tool_registry.list_tools()

    # statistics
    categories = {
        "Base": 0,
        "CPubMed core": 0,
        "CPubMed utilities": 0,
        "CPubMed relation tools": 0,
        "MedicalBook": 0,
        "Semantic Scholar": 0
    }

    for tool_name in tools:
        if tool_name == "echo":
            categories["Base"] += 1
        elif tool_name in ["cpubmed.search", "cpubmed.get_relations"]:
            categories["CPubMed core"] += 1
        elif tool_name in ["cpubmed.get_summary", "cpubmed.get_entity_type", "cpubmed.fuzzy_search"]:
            categories["CPubMed utilities"] += 1
        elif tool_name.startswith("cpubmed.query_"):
            categories["CPubMed relation tools"] += 1
        elif tool_name.startswith("medibook"):
            categories["MedicalBook"] += 1
        elif tool_name.startswith("semanticscholar"):
            categories["Semantic Scholar"] += 1

    logger.info(f"Returning tool list with {len(tools)} tools")
    return ToolListResponse(
        total_tools=len(tools),
        categories=categories,
        tools=sorted(tools)
    )


@app.get("/tools/{tool_name}", tags=["tools"])
async def get_tool_schema(tool_name: str):
    """OpenAI Function Calling Schema"""
    logger.info(f"Schema: {tool_name}")

    tool = tool_registry.get_tool(tool_name)
    if not tool:
        logger.warning(f"does not exist: {tool_name}")
        raise HTTPException(status_code=404, detail=f" '{tool_name}' does not exist")

    schema = tool.to_openai_schema()
    logger.info(f"Schema: {tool_name}")
    return schema


@app.post("/tools/execute", response_model=ToolExecuteResponse, tags=["tools"])
async def execute_tool(request: ToolExecuteRequest):
    """"""
    logger.info(f"Executing tool: {request.tool_name}")

    response = await tool_registry.execute_tool_async(
        request.tool_name,
        request.parameters
    )

    logger.info(f"Tool executed: {request.tool_name}, success: {response.success}, time: {response.execution_time:.3f}s")
    return response


@app.get("/relations", tags=["relations"])
async def get_relations():
    """"""
    logger.info("Relation information requested")

    relations_info = []
    for cn_name in RELATION_TYPES:
        en_name = RELATION_TRANSLATION[cn_name]
        tool_name = f"cpubmed.query_{en_name}"
        relations_info.append({
            "chinese": cn_name,
            "english": en_name,
            "tool": tool_name
        })

    return {
        "total": len(RELATION_TYPES),
        "relations": RELATION_TYPES,  #,
        "translation": RELATION_TRANSLATION,  #
        "details": relations_info  # ()
    }


@app.get("/stats", tags=["stats"])
async def get_stats():
    """statistics"""
    logger.info("statistics")

    tools = tool_registry.list_tools()
    categories = {}

    for tool_name in tools:
        category = "Other"
        if tool_name == "echo":
            category = "Base"
        elif tool_name.startswith("cpubmed"):
            if tool_name in ["cpubmed.search", "cpubmed.get_relations"]:
                category = "CPubMed"
            elif tool_name in ["cpubmed.get_summary", "cpubmed.get_entity_type", "cpubmed.fuzzy_search"]:
                category = "CPubMed"
            elif tool_name.startswith("cpubmed.query_"):
                category = "CPubMed"
        elif tool_name.startswith("medibook"):
            category = "MedicalBook"
        elif tool_name.startswith("semanticscholar"):
            category = "SemanticScholar"

        categories[category] = categories.get(category, 0) + 1

    return {
        "total_tools": len(tools),
        "categories": categories,
        "uptime": "N/A",
        "timestamp": datetime.now().isoformat()
    }


# ============= Main =============
if __name__ == "__main__":
    uvicorn.run(
        "tool_server:app",
        host="127.0.0.1",
        port=8766,
        workers=1,
        log_config=None
    )
