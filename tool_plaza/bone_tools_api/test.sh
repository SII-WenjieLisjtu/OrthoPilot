#!/bin/bash

# Tool Call API Server
# API

set -e

SERVER_PORT=8766
SERVER_PID_FILE=".server.pid"
SERVER_LOG="logs/server_test.log"

echo "========================================"
echo "Tool Call API Server "
echo "========================================"
echo ""

# logs
mkdir -p logs

# file
ulimit -n 65535 2>/dev/null || {
 echo "WARN file65535"
 echo ": $(ulimit -n)"
 echo ", root /etc/security/limits.conf"
 echo ""
}

#: yes or no
check_server() {
 curl -s http://localhost:8000 > /dev/null 2>&1
 return $?
}

#:
start_server() {
 echo "========================================"
 echo "API"
 echo "========================================"

 # yes or no
 if check_server; then
 echo "WARN "
 return 0
 fi

 echo "..."
 #
 nohup uvicorn tool_server:app --host 0.0.0.0 --port $SERVER_PORT --workers 20 > $SERVER_LOG 2>&1 &

 # savePID
 SERVER_PID=$!
 echo $SERVER_PID > $SERVER_PID_FILE
 echo "OK PID: $SERVER_PID"

 #
 echo "..."
 MAX_WAIT=30
 WAIT_TIME=0

 while [ $WAIT_TIME -lt $MAX_WAIT ]; do
 if check_server; then
 echo "OK !"
 echo ""
 return 0
 fi
 sleep 1
 WAIT_TIME=$((WAIT_TIME + 1))
 echo -n "."
 done

 echo ""
 echo "ERROR "
 return 1
}

#:
stop_server() {
 echo ""
 echo "========================================"
 echo "API"
 echo "========================================"

 if [ -f $SERVER_PID_FILE ]; then
 SERVER_PID=$(cat $SERVER_PID_FILE)
 if kill -0 $SERVER_PID 2>/dev/null; then
 echo " (PID: $SERVER_PID)..."
 kill $SERVER_PID
 sleep 2

 #,
 if kill -0 $SERVER_PID 2>/dev/null; then
 echo "..."
 kill -9 $SERVER_PID
 fi

 echo "OK "
 fi
 rm -f $SERVER_PID_FILE
 else
 echo "WARN PID file"
 fi
}

#: API
run_api_tests() {
 echo "========================================"
 echo "API"
 echo "========================================"
 python tools/test/test_api.py
 return $?
}

#
SKIP_SERVER_START=false
SERVER_STARTED_BY_SCRIPT=false

#
if [ "$1" == "--skip-server" ]; then
 SKIP_SERVER_START=true
 echo "skip()"
fi

# (skip)
if [ "$SKIP_SERVER_START" = false ]; then
 # trap,
 trap stop_server EXIT INT TERM

 start_server
 if [ $? -ne 0 ]; then
 echo "ERROR "
 exit 1
 fi
 SERVER_STARTED_BY_SCRIPT=true
else
 # yes or no
 if ! check_server; then
 echo "ERROR, "
 exit 1
 fi
 echo "OK "
 echo ""
 SERVER_STARTED_BY_SCRIPT=false
fi

#
run_api_tests
TEST_RESULT=$?

# result
echo ""
echo "========================================"
if [ $TEST_RESULT -eq 0 ]; then
 echo "OK !"
else
 echo "ERROR "
fi
echo "========================================"

exit $TEST_RESULT
