# Tool Call API Server

高性能医学知识图谱与学术论文搜索API服务，基于FastAPI构建，支持2000+高并发请求，提供53个专业工具。

## 快速开始

### 1. 安装依赖

```bash
# Activate conda environment (optional)
conda activate note

# Install dependencies
pip install -r requirements.txt
```

### 2. 环境配置

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
# 必需配置：
# - OPENAI_API_KEY: OpenAI API密钥（MedicalBook工具需要）
# - SEMANTIC_SCHOLAR_API_KEY: Semantic Scholar API密钥（论文搜索工具需要）
#
# 可选配置：
# - OPENAI_API_BASE: OpenAI API基础URL（默认为官方API）
# - SERVER_PORT: 服务器端口（默认8766）
# - SERVER_WORKERS: 工作进程数（默认20）
```

**配置说明**：
- **OpenAI API**: 用于MedicalBook工具的LLM模式，获取地址：https://YOUR_PROVIDER_API_KEYS_PAGE
- **Semantic Scholar API**: 用于学术论文搜索，免费申请：https://YOUR_SCHOLAR_API_DOCS
- 如果某个API未配置，相应工具将无法使用，但不影响其他工具

**兼容性**: 项目仍支持旧的 `.openai` 配置文件格式，但推荐使用统一的 `.env` 配置。

### 3. 启动服务器

```bash
# Option 1: Use start script
bash start_server.sh

# Option 2: Direct uvicorn command
uvicorn tool_server:app --host 0.0.0.0 --port 8766 --workers 1
```

### 4. 访问API文档

- Swagger UI: http://YOUR_HOST:YOUR_PORT
- ReDoc: http://YOUR_HOST:YOUR_PORT

### 5. 运行测试

```bash
# 自动启动服务器并运行API测试
bash test.sh

# 使用已运行的服务器进行测试（跳过服务器启动）
bash test.sh --skip-server

# 直接运行测试（需要服务器已启动）
python tools/test/test_api.py
```

**测试说明**：
- 所有测试通过HTTP API进行，测试真实的API调用场景
- 包含10个测试用例，覆盖所有主要功能（含Semantic Scholar论文搜索）
- 包含2000个并发请求的性能测试，验证高并发能力

## API使用示例

```python
import requests

# Execute a tool
response = requests.post(
    "http://YOUR_HOST:YOUR_PORT",
    json={
        "tool_name": "cpubmed.search",
        "parameters": {
            "entity": "糖尿病",
            "relation": "药物治疗",
            "limit": 5
        }
    }
)

result = response.json()
print(result)
```

详细API文档请参考：[API_GUIDE.md](API_GUIDE.md)

---

## 工具概览

**总计：53个工具**

### 工具分类

| 分类 | 工具数 | 说明 |
|------|--------|------|
| 基础工具 | 1 | Echo测试工具 |
| CPubMed核心 | 2 | 通用查询、关系查询 |
| CPubMed实用 | 3 | 数据概览、实体类型、模糊搜索 |
| CPubMed关系 | 45 | 45种关系类型的专用查询工具 |
| MedicalBook | 1 | 医学书籍检索 |
| SemanticScholar | 1 | 学术论文搜索 |

### 常用工具

```python
# 1. 通用知识图谱查询
POST /tools/execute
{
  "tool_name": "cpubmed.search",
  "parameters": {
    "entity": "糖尿病",
    "relation": "药物治疗",
    "limit": 10
  }
}

# 2. 关系专用工具（更简洁）
POST /tools/execute
{
  "tool_name": "cpubmed.query_drug_treatment",
  "parameters": {
    "entity": "糖尿病",
    "limit": 10
  }
}

# 3. 模糊搜索实体
POST /tools/execute
{
  "tool_name": "cpubmed.fuzzy_search",
  "parameters": {
    "keyword": "肺癌",
    "threshold": 0.7,
    "limit": 5
  }
}

# 4. 医学书籍检索
POST /tools/execute
{
  "tool_name": "medibook.search",
  "parameters": {
    "query": "糖尿病的症状",
    "search_mode": "embedding"
  }
}

# 5. 学术论文搜索
POST /tools/execute
{
  "tool_name": "semanticscholar.search",
  "parameters": {
    "query": "machine learning in healthcare",
    "limit": 10
  }
}
```

完整工具列表：[tools/cpubmed/TOOLS.md](tools/cpubmed/TOOLS.md)

---

## 性能特性

- ✅ **高并发**: 支持50+并发请求
- ✅ **异步处理**: FastAPI + asyncio + ThreadPoolExecutor
- ✅ **智能日志**: 自动截断、日志轮转（10MB/文件，保留5个备份）
- ✅ **完整文档**: Swagger UI + ReDoc自动生成
- ✅ **容错设计**: 统一错误处理和响应格式

---

## Setup Data (CPubMed)

If you have the original `CPubMed-KGv2_0.txt` file, follow these steps to prepare the data:

### Step 1: Convert TXT to CSV

```bash
cd tools/data/cpubmed
python txt2csv.py
```

This will:
- Read `CPubMed-KGv2_0.txt` (tab-separated, 266MB)
- Convert to `CPubMed-kGv2_0.csv` (comma-separated, 271MB)
- Process ~4.58M triples
- Take about 1-2 minutes

### Step 2: Build Index (Automatic)

The index is built automatically when the server starts or on first API call:

**Option 1: Build during first API call**
```bash
# Start server (index will build on first CPubMed query)
bash start_server.sh

# Make first query (triggers index build)
curl -X POST http://YOUR_HOST:YOUR_PORT \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"cpubmed.search","parameters":{"entity":"糖尿病","limit":5}}'
```

**Option 2: Pre-build by starting server**
The index will be created automatically when you start the server:
```bash
bash start_server.sh
# Index builds during server initialization
```

### Step 3 (Optional): Generate Statistics

```bash
cd tools/data/cpubmed
python static.py
```

This generates:
- `entity.csv` - Entity statistics (2.08M entities)
- `relation.csv` - Relation statistics (45 relations)
- `type.csv` - Entity type statistics (12 types)
- `data_statistic.log` - Processing log

### File Structure

```
tools/data/cpubmed/
├── CPubMed-KGv2_0.txt      # Original data (required)
├── CPubMed-kGv2_0.csv      # Converted CSV (auto-generated)
├── kg_index.pkl            # Search index (auto-generated)
├── entity.csv              # Statistics (optional)
├── relation.csv            # Statistics (optional)
├── type.csv                # Statistics (optional)
├── txt2csv.py              # Conversion script
├── static.py               # Statistics script
└── README.md               # Data documentation
```

### Note

- Only `CPubMed-KGv2_0.txt` is required as input
- All other files are generated automatically
- Index is cached for fast subsequent runs
- You can delete `kg_index.pkl` to rebuild the index

## Project Structure

```
agent/
├── tools/                 # Tool call module
│   ├── base/              # Base classes
│   ├── utils/             # Utility functions
│   ├── cpubmed/           # Medical KG tools (50 tools)
│   ├── medibook/          # Medical book tool
│   ├── semanticscholar/   # Academic paper search tool
│   ├── data/              # Data files
│   └── test/              # API test files
├── tool_server.py         # FastAPI server
├── logger_config.py       # Logging configuration
├── start_server.sh        # Server startup script
├── test.sh                # Automated test script
├── requirements.txt       # Python dependencies
├── .env.example           # Environment config template
├── API_GUIDE.md           # API usage guide
└── readme.md              # This file
```

## Core Features

### 1. RESTful API Server

- **FastAPI**: Modern, fast web framework
- **Async Processing**: Support 50+ concurrent requests
- **Auto Documentation**: Swagger UI + ReDoc
- **Unified Response**: Consistent JSON response format

### 2. Rich Tool Ecosystem

**53 Tools Available:**
- 1 Echo tool (testing)
- 2 CPubMed core tools (search, relations)
- 3 CPubMed utility tools (summary, entity type, fuzzy search)
- 45 CPubMed relation-specific tools
- 1 MedicalBook tool (medical book search)
- 1 SemanticScholar tool (academic paper search)

### 3. CPubMed Knowledge Graph

Query 4.58M medical triples via API:

```bash
curl -X POST http://YOUR_HOST:YOUR_PORT \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "cpubmed.search",
    "parameters": {
      "entity": "糖尿病",
      "relation": "药物治疗",
      "limit": 10
    }
  }'
```

Supports 45 relation types:
- Treatment: 药物治疗, 辅助治疗, 手术治疗, 放射治疗, 化疗, 预防
- Examination: 实验室检查, 影像学检查, 辅助检查, 内窥镜检查, 筛查
- Symptoms: 临床表现, 病因, 病理分型, 并发症, 鉴别诊断, 高危因素
- Epidemiology: 发病率, 发病部位, 多发群体, 发病年龄, 死亡率

### 4. Intelligent Logging

- Automatic log rotation (10MB per file, keep 5 backups)
- Smart truncation (console: 500 chars, file: 2000 chars)
- Separate logs for server, tools, and retrieval

## API Usage Flow

1. **Start Server**:
   ```bash
   bash start_server.sh
   ```

2. **Get Available Tools**:
   ```bash
   curl http://YOUR_HOST:YOUR_PORT
   ```

3. **Get Tool Schema**:
   ```bash
   curl http://YOUR_HOST:YOUR_PORT
   ```

4. **Execute Tool**:
   ```bash
   curl -X POST http://YOUR_HOST:YOUR_PORT \
     -H "Content-Type: application/json" \
     -d '{"tool_name":"echo","parameters":{"message":"Hello","repeat":3}}'
   ```

5. **Get Response**:
   ```json
   {
     "success": true,
     "tool_name": "echo",
     "data": "Hello Hello Hello",
     "error": null,
     "execution_time": 0.002,
     "timestamp": "2025-01-17T10:30:00"
   }
   ```

## Develop New Tools

### Step 1: Create Tool Class

```python
from tools.base import Tool, ToolParameter
from typing import List, Dict, Any

class MyCustomTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_custom.tool",
            description="My custom tool description"
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="param1",
                type="string",
                description="Parameter description",
                required=True
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        # Tool implementation
        param1 = parameters.get("param1")
        return f"Result: {param1}"
```

### Step 2: Register in Server

Add to `tool_server.py`:
```python
from my_module import MyCustomTool

# In ToolRegistry._initialize_tools()
self.register_tool(MyCustomTool())
```

### Step 3: Test via API

```bash
curl -X POST http://YOUR_HOST:YOUR_PORT \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"my_custom.tool","parameters":{"param1":"test"}}'
```

## Performance

### Server Performance
- **Concurrent Requests**: 50+ simultaneous requests
- **Response Time**: < 50ms for simple tools
- **Throughput**: 100+ QPS on standard hardware

### Data Processing
- **CPubMed Index Build**: 1-2 min (4.58M triples, first time only)
- **Index Load**: < 1s (cached)
- **Query Performance**: < 10ms per query
- **Fuzzy Search**: < 50ms (depends on threshold and limit)

### Logs
- **Log Rotation**: Automatic (10MB/file)
- **Log Retention**: 5 backup files
- **Console Output**: Truncated at 500 chars
- **File Output**: Truncated at 2000 chars

## Documentation

- **API Guide**: [API_GUIDE.md](API_GUIDE.md) - Complete API documentation
- **Tool List**: [tools/cpubmed/TOOLS.md](tools/cpubmed/TOOLS.md) - All 50 tools
- **Data Info**: [tools/data/cpubmed/README.md](tools/data/cpubmed/README.md) - Data description

## License

For learning and research use only.
