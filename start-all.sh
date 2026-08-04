#!/usr/bin/env bash
set -e

SAT_EDGE_DIR=${SAT_EDGE_DIR:-"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"}
EDGE_WORKSPACE=${EDGE_WORKSPACE:-"$(dirname "$SAT_EDGE_DIR")"}
YOLO26_DIR=${YOLO26_DIR:-"$EDGE_WORKSPACE/yolo26-obb_server"}
LOCAL_LLM_DIR=${LOCAL_LLM_DIR:-"$EDGE_WORKSPACE/local-llm-service"}
LOG_DIR=${LOG_DIR:-"$SAT_EDGE_DIR/logs"}
mkdir -p "$LOG_DIR"

start_if_down() {
  local name=$1 port=$2 cmd=$3 log=$4
  if curl -s -o /dev/null --connect-timeout 2 "http://localhost:$port" >/dev/null 2>&1; then
    echo "[$name] already running on :$port"
  else
    echo "[$name] starting on :$port ..."
    nohup bash -c "$cmd" > "$log" 2>&1 &
    disown
    echo "[$name] PID=$!"
  fi
}

start_if_down "YOLO26"   8003 "cd \"$YOLO26_DIR\" && uv run uvicorn obb_geo_api_server:app --host 0.0.0.0 --port 8003" "$LOG_DIR/yolo26.log"
start_if_down "Agent"    9001 "cd \"$SAT_EDGE_DIR/yolo_agent-main\" && uv run uvicorn backend.app:app --host 0.0.0.0 --port 9001" "$LOG_DIR/agent.log"
start_if_down "Frontend" 5173 "cd \"$SAT_EDGE_DIR\" && npx vite --host 0.0.0.0 --port 5173" "$LOG_DIR/frontend.log"
start_if_down "LocalLLM" 8080 "cd \"$LOCAL_LLM_DIR\" && uv run uvicorn main:app --host 0.0.0.0 --port 8080" "$LOG_DIR/local-llm.log"

echo ""
sleep 3
echo "=== Status ==="
for port in 8003 9001 5173 8080; do
  status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://localhost:$port" 2>/dev/null || echo "DOWN")
  printf "Port %s: %s\n" "$port" "$status"
done
