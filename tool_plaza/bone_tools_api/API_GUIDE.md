# Tool Call API Server 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
# 方式1: 使用启动脚本
bash start_server.sh

# 方式2: 直接使用uvicorn
uvicorn tool_server:app --host 0.0.0.0 --port 8766 --workers 1
```

### 3. 访问API文档

启动后访问：
- Swagger UI: http://YOUR_HOST:YOUR_PORT
- ReDoc: http://YOUR_HOST:YOUR_PORT

### 4. 运行测试

```bash
# 自动启动服务器并测试
bash test.sh

# 使用已运行的服务器测试
bash test.sh --skip-server
```

---

## API端点

### 系统端点

#### GET /
根路径，返回服务基本信息

**响应示例：**
```json
{
  "service": "Tool Call API Server",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "total_tools": 50
}
```

#### GET /health
健康检查

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-17T10:30:00",
  "tools_loaded": 50
}
```

#### GET /stats
服务器统计信息

**响应示例：**
```json
{
  "total_tools": 50,
  "categories": {
    "基础工具": 1,
    "CPubMed核心": 2,
    "CPubMed实用": 3,
    "CPubMed关系": 45,
    "MedicalBook": 1
  },
  "timestamp": "2025-01-17T10:30:00"
}
```

---

### 工具管理端点

#### GET /tools
获取所有工具列表

**响应示例：**
```json
{
  "total_tools": 50,
  "categories": {
    "基础工具": 1,
    "CPubMed核心工具": 2,
    "CPubMed实用工具": 3,
    "CPubMed关系工具": 45,
    "MedicalBook工具": 1
  },
  "tools": [
    "echo",
    "cpubmed.search",
    "cpubmed.get_relations",
    "..."
  ]
}
```

#### GET /tools/{tool_name}
获取工具的OpenAI Function Calling Schema

**请求示例：**
```bash
curl http://YOUR_HOST:YOUR_PORT
```

**响应示例：**
```json
{
  "type": "function",
  "function": {
    "name": "echo",
    "description": "回显工具，返回输入的消息",
    "parameters": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "要回显的消息"
        },
        "repeat": {
          "type": "integer",
          "description": "重复次数",
          "default": 1
        }
      },
      "required": ["message"]
    }
  }
}
```

---

### 工具执行端点

#### POST /tools/execute
执行指定工具

**请求体：**
```json
{
  "tool_name": "echo",
  "parameters": {
    "message": "Hello API!",
    "repeat": 3
  }
}
```

**响应示例：**
```json
{
  "success": true,
  "tool_name": "echo",
  "data": "Hello API! Hello API! Hello API!",
  "error": null,
  "execution_time": 0.002,
  "timestamp": "2025-01-17T10:30:00.123456"
}
```

---

### 数据信息端点

#### GET /relations
获取所有CPubMed关系类型

**响应示例：**
```json
{
  "total": 45,
  "relations": [
    "药物治疗",
    "辅助治疗",
    "手术治疗",
    "..."
  ]
}
```

---

## 使用示例

### Python示例

```python
import requests
import json

BASE_URL = "http://YOUR_HOST:YOUR_PORT"

# 1. 获取工具列表
response = requests.get(f"{BASE_URL}/tools")
tools = response.json()
print(f"可用工具数: {tools['total_tools']}")

# 2. 执行Echo工具
payload = {
    "tool_name": "echo",
    "parameters": {
        "message": "Hello",
        "repeat": 3
    }
}
response = requests.post(f"{BASE_URL}/tools/execute", json=payload)
result = response.json()
print(f"结果: {result['data']}")

# 3. 查询CPubMed
payload = {
    "tool_name": "cpubmed.search",
    "parameters": {
        "entity": "糖尿病",
        "relation": "药物治疗",
        "limit": 5
    }
}
response = requests.post(f"{BASE_URL}/tools/execute", json=payload)
result = response.json()
if result['success']:
    data = json.loads(result['data'])
    print(f"找到 {data['total_results']} 条结果")

# 4. 使用关系专用工具
payload = {
    "tool_name": "cpubmed.query_drug_treatment",
    "parameters": {
        "entity": "高血压",
        "limit": 10
    }
}
response = requests.post(f"{BASE_URL}/tools/execute", json=payload)
result = response.json()
```

### JavaScript/Node.js示例

```javascript
const axios = require('axios');

const BASE_URL = 'http://YOUR_HOST:YOUR_PORT';

// 执行工具
async function executeTool(toolName, parameters) {
    try {
        const response = await axios.post(`${BASE_URL}/tools/execute`, {
            tool_name: toolName,
            parameters: parameters
        });

        return response.data;
    } catch (error) {
        console.error('Error:', error.message);
        return null;
    }
}

// 使用示例
(async () => {
    // 查询CPubMed
    const result = await executeTool('cpubmed.search', {
        entity: '糖尿病',
        relation: '药物治疗',
        limit: 5
    });

    if (result && result.success) {
        const data = JSON.parse(result.data);
        console.log(`找到 ${data.total_results} 条结果`);
    }
})();
```

### cURL示例

```bash
# 获取工具列表
curl http://YOUR_HOST:YOUR_PORT

# 获取工具信息
curl http://YOUR_HOST:YOUR_PORT

# 执行工具
curl -X POST http://YOUR_HOST:YOUR_PORT \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "echo",
    "parameters": {
      "message": "Hello",
      "repeat": 3
    }
  }'

# 查询CPubMed
curl -X POST http://YOUR_HOST:YOUR_PORT \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "cpubmed.search",
    "parameters": {
      "entity": "糖尿病",
      "relation": "药物治疗",
      "limit": 5
    }
  }'
```

---

## 并发性能

服务器支持高并发请求处理：
- 使用异步FastAPI框架
- 线程池执行CPU密集型工具（50个工作线程）
- 支持同时处理50+并发请求

**并发测试：**
```python
import asyncio
import httpx

async def test_concurrent():
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(50):
            task = client.post(
                "http://YOUR_HOST:YOUR_PORT",
                json={
                    "tool_name": "echo",
                    "parameters": {"message": f"Request {i}", "repeat": 1}
                }
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        success = sum(1 for r in responses if r.status_code == 200)
        print(f"成功: {success}/50")

asyncio.run(test_concurrent())
```

---

## 日志系统

日志文件位于 `logs/` 目录：

- `server.log` - 服务器日志
- `tool_execution.log` - 工具执行日志
- `kg_retriever.log` - 知识图谱检索日志

日志特性：
- 自动轮转（单文件最大10MB）
- 保留5个备份文件
- 自动截断过长输出（控制台500字符，文件2000字符）

---

## 错误处理

所有工具执行失败都会返回统一格式：

```json
{
  "success": false,
  "tool_name": "tool_name",
  "data": null,
  "error": "错误描述信息",
  "execution_time": 0.002,
  "timestamp": "2025-01-17T10:30:00"
}
```

常见错误：
- `工具不存在` - 工具名称错误
- `参数错误` - 缺少必需参数或参数类型错误
- `执行异常` - 工具执行过程中出现异常

---

## 最佳实践

1. **并发控制**：虽然服务器支持高并发，但建议控制客户端并发数在50以内

2. **超时设置**：某些工具（如CPubMed首次查询需要构建索引）可能需要较长时间，建议设置30秒超时

3. **错误重试**：对于网络错误，建议实现指数退避重试策略

4. **日志监控**：定期检查日志文件，监控服务器运行状态

5. **资源管理**：长时间运行后，考虑定期重启服务器以释放资源

---

## 工具分类

### 基础工具 (1个)
- `echo` - 回显测试工具

### CPubMed核心工具 (2个)
- `cpubmed.search` - 通用知识图谱查询
- `cpubmed.get_relations` - 获取实体所有关系

### CPubMed实用工具 (3个)
- `cpubmed.get_summary` - 数据库概览
- `cpubmed.get_entity_type` - 查询实体类型
- `cpubmed.fuzzy_search` - 模糊搜索实体

### CPubMed关系工具 (45个)
基于关系类型的专用查询工具，如：
- `cpubmed.query_drug_treatment` - 药物治疗
- `cpubmed.query_clinical_manifestation` - 临床表现
- `cpubmed.query_complication` - 并发症
- 等（完整列表见 `tools/cpubmed/TOOLS.md`）

### MedicalBook工具 (1个)
- `medibook.search` - 医学书籍检索

---

## 技术栈

- **Web框架**: FastAPI
- **ASGI服务器**: Uvicorn
- **并发处理**: asyncio + ThreadPoolExecutor
- **日志**: Python logging + RotatingFileHandler
- **数据处理**: Pandas
- **ML/Embedding**: FlagEmbedding
- **API客户端**: OpenAI

---

## 故障排查

### 服务器无法启动

1. 检查端口是否被占用：
```bash
lsof -i:8766
```

2. 检查依赖是否安装：
```bash
pip install -r requirements.txt
```

3. 查看日志：
```bash
tail -f logs/server.log
```

### 工具执行失败

1. 检查工具名称是否正确：
```bash
curl http://YOUR_HOST:YOUR_PORT
```

2. 检查参数格式：
```bash
curl http://YOUR_HOST:YOUR_PORT
```

3. 查看执行日志：
```bash
tail -f logs/tool_execution.log
```

### 性能问题

1. 检查线程池大小（默认50）
2. 监控日志文件大小
3. 考虑使用多worker模式（需要修改启动命令）

---

## 更多信息

- 工具详细列表：`tools/cpubmed/TOOLS.md`
- 数据说明：`tools/data/cpubmed/README.md`
- 项目README：`readme.md`
