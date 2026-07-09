#!/bin/bash

# Tool Call API Server 启动脚本
# source activate note
cd /path/to/orthopilot/tool_plaza/bone_tools_api

PORT=8766
HOST="YOUR_HOST"
WORKERS=20

echo "========================================"
echo "Tool Call API Server"
echo "========================================"
echo ""
echo "配置:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo ""
echo "API文档: http://YOUR_HOST:YOUR_PORT"
echo "========================================"
echo ""

# 创建logs目录
mkdir -p logs

# 启动服务器
uvicorn tool_server:app --host $HOST --port $PORT --workers $WORKERS
