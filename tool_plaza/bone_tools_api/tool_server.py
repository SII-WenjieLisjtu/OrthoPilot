"""Tool Call API Server

高性能异步API服务器，支持工具调用和高并发
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

# 加载环境变量
# 优先加载 .env 文件，如果不存在则尝试加载 .openai 文件（向后兼容）
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


# ============= 数据模型 =============
class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolExecuteResponse(BaseModel):
    """工具执行响应"""
    success: bool = Field(..., description="执行是否成功")
    tool_name: str = Field(..., description="工具名称")
    data: Any = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(..., description="执行时间(秒)")
    timestamp: str = Field(..., description="时间戳")


class ToolListResponse(BaseModel):
    """工具列表响应"""
    total_tools: int = Field(..., description="工具总数")
    categories: Dict[str, int] = Field(..., description="分类统计")
    tools: List[str] = Field(..., description="工具名称列表")


# ============= 工具管理器 =============
class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.executor = ThreadPoolExecutor(max_workers=50)  # 线程池用于CPU密集型任务
        self._initialize_tools()

    def _initialize_tools(self):
        """初始化所有工具"""
        logger.info("开始初始化工具注册中心...")

        try:
            # 基础工具
            logger.info("注册基础工具...")
            self.register_tool(EchoTool())

            # CPubMed核心工具
            logger.info("注册CPubMed核心工具...")
            self.register_tool(CPubMedTool())
            self.register_tool(CPubMedRelationTool())

            # CPubMed实用工具
            logger.info("注册CPubMed实用工具...")
            self.register_tool(CPubMedDatabaseSummaryTool())
            self.register_tool(CPubMedGetEntityTypeTool())
            self.register_tool(CPubMedFuzzySearchTool())

            # CPubMed关系专用工具
            logger.info("注册CPubMed关系专用工具（45个）...")
            for relation_name, tool_class in RELATION_TOOL_CLASSES.items():
                try:
                    tool = tool_class()
                    self.register_tool(tool)
                except Exception as e:
                    logger.error(f"注册关系工具失败 {relation_name}: {e}")

            # MedicalBook工具
            logger.info("注册MedicalBook工具...")
            self.register_tool(MedicalBookTool())

            # Semantic Scholar工具
            logger.info("注册Semantic Scholar工具...")
            self.register_tool(SemanticScholarSearchTool())

            logger.info(f"工具注册完成，共注册 {len(self.tools)} 个工具")

        except Exception as e:
            logger.error(f"工具初始化失败: {e}", exc_info=True)
            raise

    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.debug(f"已注册工具: {tool.name}")

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self.tools.keys())

    async def execute_tool_async(self, tool_name: str, parameters: Dict[str, Any]) -> ToolExecuteResponse:
        """异步执行工具"""
        start_time = time.time()

        # 记录工具执行开始，截断参数长度
        params_str = truncate_text(str(parameters), 200)
        tool_logger.info(f"开始执行工具: {tool_name}, 参数: {params_str}")

        tool = self.get_tool(tool_name)
        if not tool:
            tool_logger.error(f"工具不存在: {tool_name}")
            return ToolExecuteResponse(
                success=False,
                tool_name=tool_name,
                error=f"工具 '{tool_name}' 不存在",
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )

        try:
            # 在线程池中执行工具（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                tool.execute,
                parameters
            )

            execution_time = time.time() - start_time

            # 记录执行结果，截断数据长度
            if response.success:
                data_preview = truncate_text(str(response.data), 300)
                tool_logger.info(f"工具执行成功: {tool_name}, 耗时: {execution_time:.3f}s, 数据预览: {data_preview}")
            else:
                tool_logger.warning(f"工具执行失败: {tool_name}, 耗时: {execution_time:.3f}s, 错误: {response.error}")

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
            error_msg = f"工具执行异常: {str(e)}"
            tool_logger.error(f"{error_msg}", exc_info=True)

            return ToolExecuteResponse(
                success=False,
                tool_name=tool_name,
                error=error_msg,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )


# ============= FastAPI应用 =============
app = FastAPI(
    title="Tool Call API Server",
    description="医学知识图谱工具调用API服务",
    version="0.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局工具注册中心
tool_registry = None


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    global tool_registry
    logger.info("=" * 80)
    logger.info("Tool Call API Server 启动中...")
    logger.info("=" * 80)

    try:
        tool_registry = ToolRegistry()
        logger.info("服务器启动成功！")
        logger.info(f"已注册工具数: {len(tool_registry.tools)}")
        logger.info(f"API文档: http://YOUR_HOST:YOUR_PORT")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"服务器启动失败: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Tool Call API Server 关闭中...")
    if tool_registry:
        tool_registry.executor.shutdown(wait=True)
    logger.info("服务器已关闭")


# ============= API路由 =============

@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    logger.debug("访问根路径")
    return {
        "service": "Tool Call API Server",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "total_tools": len(tool_registry.tools) if tool_registry else 0
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    logger.debug("健康检查")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tools_loaded": len(tool_registry.tools) if tool_registry else 0
    }


@app.get("/tools", response_model=ToolListResponse, tags=["工具管理"])
async def list_tools():
    """获取所有工具列表"""
    logger.info("请求工具列表")

    tools = tool_registry.list_tools()

    # 分类统计
    categories = {
        "基础工具": 0,
        "CPubMed核心工具": 0,
        "CPubMed实用工具": 0,
        "CPubMed关系工具": 0,
        "MedicalBook工具": 0,
        "SemanticScholar工具": 0
    }

    for tool_name in tools:
        if tool_name == "echo":
            categories["基础工具"] += 1
        elif tool_name in ["cpubmed.search", "cpubmed.get_relations"]:
            categories["CPubMed核心工具"] += 1
        elif tool_name in ["cpubmed.get_summary", "cpubmed.get_entity_type", "cpubmed.fuzzy_search"]:
            categories["CPubMed实用工具"] += 1
        elif tool_name.startswith("cpubmed.query_"):
            categories["CPubMed关系工具"] += 1
        elif tool_name.startswith("medibook"):
            categories["MedicalBook工具"] += 1
        elif tool_name.startswith("semanticscholar"):
            categories["SemanticScholar工具"] += 1

    logger.info(f"返回工具列表，共 {len(tools)} 个工具")
    return ToolListResponse(
        total_tools=len(tools),
        categories=categories,
        tools=sorted(tools)
    )


@app.get("/tools/{tool_name}", tags=["工具管理"])
async def get_tool_schema(tool_name: str):
    """获取工具的OpenAI Function Calling Schema"""
    logger.info(f"请求工具Schema: {tool_name}")

    tool = tool_registry.get_tool(tool_name)
    if not tool:
        logger.warning(f"工具不存在: {tool_name}")
        raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")

    schema = tool.to_openai_schema()
    logger.info(f"返回工具Schema: {tool_name}")
    return schema


@app.post("/tools/execute", response_model=ToolExecuteResponse, tags=["工具执行"])
async def execute_tool(request: ToolExecuteRequest):
    """执行工具"""
    logger.info(f"收到工具执行请求: {request.tool_name}")

    response = await tool_registry.execute_tool_async(
        request.tool_name,
        request.parameters
    )

    logger.info(f"工具执行响应: {request.tool_name}, 成功: {response.success}, 耗时: {response.execution_time:.3f}s")
    return response


@app.get("/relations", tags=["数据信息"])
async def get_relations():
    """获取所有关系类型及中英文翻译对照"""
    logger.info("请求关系类型列表")

    # 构建完整的关系信息
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
        "relations": RELATION_TYPES,  # 中文列表，保持向后兼容
        "translation": RELATION_TRANSLATION,  # 完整翻译表
        "details": relations_info  # 详细信息（包含工具名）
    }


@app.get("/stats", tags=["系统"])
async def get_stats():
    """获取服务器统计信息"""
    logger.info("请求统计信息")

    tools = tool_registry.list_tools()
    categories = {}

    for tool_name in tools:
        category = "其他"
        if tool_name == "echo":
            category = "基础工具"
        elif tool_name.startswith("cpubmed"):
            if tool_name in ["cpubmed.search", "cpubmed.get_relations"]:
                category = "CPubMed核心"
            elif tool_name in ["cpubmed.get_summary", "cpubmed.get_entity_type", "cpubmed.fuzzy_search"]:
                category = "CPubMed实用"
            elif tool_name.startswith("cpubmed.query_"):
                category = "CPubMed关系"
        elif tool_name.startswith("medibook"):
            category = "MedicalBook"
        elif tool_name.startswith("semanticscholar"):
            category = "SemanticScholar"

        categories[category] = categories.get(category, 0) + 1

    return {
        "total_tools": len(tools),
        "categories": categories,
        "uptime": "N/A",  # 可以添加运行时间统计
        "timestamp": datetime.now().isoformat()
    }


# ============= 主函数 =============
if __name__ == "__main__":
    uvicorn.run(
        "tool_server:app",
        host="YOUR_HOST",
        port=8766,
        workers=1,
        log_config=None  # 使用自定义日志配置
    )
