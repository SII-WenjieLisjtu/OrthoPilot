#!/bin/bash

# Tool Call API Server 测试脚本
# 自动启动服务器并运行API测试

set -e

SERVER_PORT=8766
SERVER_PID_FILE=".server.pid"
SERVER_LOG="logs/server_test.log"

echo "========================================"
echo "Tool Call API Server 测试套件"
echo "========================================"
echo ""

# 创建logs目录
mkdir -p logs

# 增加文件描述符限制以支持高并发测试
ulimit -n 65535 2>/dev/null || {
    echo "⚠ 无法设置文件描述符限制为65535"
    echo "  当前限制: $(ulimit -n)"
    echo "  如需高并发测试，请以root运行或修改 /etc/security/limits.conf"
    echo ""
}

# 函数：检查服务器是否运行
check_server() {
    curl -s http://YOUR_HOST:YOUR_PORT > /dev/null 2>&1
    return $?
}

# 函数：启动服务器
start_server() {
    echo "========================================"
    echo "启动API服务器"
    echo "========================================"

    # 检查服务器是否已在运行
    if check_server; then
        echo "⚠ 服务器已在运行"
        return 0
    fi

    echo "启动服务器进程..."
    # 在后台启动服务器
    nohup uvicorn tool_server:app --host 0.0.0.0 --port $SERVER_PORT --workers 20 > $SERVER_LOG 2>&1 &

    # 保存PID
    SERVER_PID=$!
    echo $SERVER_PID > $SERVER_PID_FILE
    echo "✓ 服务器PID: $SERVER_PID"

    # 等待服务器启动
    echo "等待服务器启动..."
    MAX_WAIT=30
    WAIT_TIME=0

    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        if check_server; then
            echo "✓ 服务器启动成功！"
            echo ""
            return 0
        fi
        sleep 1
        WAIT_TIME=$((WAIT_TIME + 1))
        echo -n "."
    done

    echo ""
    echo "✗ 服务器启动超时"
    return 1
}

# 函数：停止服务器
stop_server() {
    echo ""
    echo "========================================"
    echo "停止API服务器"
    echo "========================================"

    if [ -f $SERVER_PID_FILE ]; then
        SERVER_PID=$(cat $SERVER_PID_FILE)
        if kill -0 $SERVER_PID 2>/dev/null; then
            echo "停止服务器进程 (PID: $SERVER_PID)..."
            kill $SERVER_PID
            sleep 2

            # 如果还在运行，强制结束
            if kill -0 $SERVER_PID 2>/dev/null; then
                echo "强制结束服务器进程..."
                kill -9 $SERVER_PID
            fi

            echo "✓ 服务器已停止"
        fi
        rm -f $SERVER_PID_FILE
    else
        echo "⚠ 未找到服务器PID文件"
    fi
}

# 函数：运行API测试
run_api_tests() {
    echo "========================================"
    echo "运行API测试"
    echo "========================================"
    python tools/test/test_api.py
    return $?
}

# 主流程
SKIP_SERVER_START=false
SERVER_STARTED_BY_SCRIPT=false

# 检查命令行参数
if [ "$1" == "--skip-server" ]; then
    SKIP_SERVER_START=true
    echo "跳过服务器启动（使用现有服务器）"
fi

# 启动服务器（除非跳过）
if [ "$SKIP_SERVER_START" = false ]; then
    # 设置trap，确保脚本退出时停止服务器
    trap stop_server EXIT INT TERM

    start_server
    if [ $? -ne 0 ]; then
        echo "✗ 服务器启动失败"
        exit 1
    fi
    SERVER_STARTED_BY_SCRIPT=true
else
    # 检查服务器是否运行
    if ! check_server; then
        echo "✗ 服务器未运行，请先启动服务器"
        exit 1
    fi
    echo "✓ 检测到运行中的服务器"
    echo ""
    SERVER_STARTED_BY_SCRIPT=false
fi

# 运行测试
run_api_tests
TEST_RESULT=$?

# 显示测试结果
echo ""
echo "========================================"
if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ 所有测试通过！"
else
    echo "✗ 测试失败"
fi
echo "========================================"

exit $TEST_RESULT
