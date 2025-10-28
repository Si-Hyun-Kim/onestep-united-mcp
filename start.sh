#!/bin/bash
# start_all.sh - 모든 서비스 시작

echo "╔════════════════════════════════════════════════╗"
echo "║  🚀 Starting AI Security System               ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# 색상
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 현재 디렉토리
cd "$(dirname "$0")"

# 가상환경 활성화
source venv/bin/activate

# PID 저장 디렉토리
mkdir -p .pids

echo -e "${BLUE}[1/5] Ollama 서버 확인 중...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "  ${YELLOW}⚠️  Ollama가 실행되지 않았습니다!${NC}"
    echo -e "  다른 터미널에서 'ollama serve' 실행하세요."
    echo -e "  또는 백그라운드로 시작: nohup ollama serve > logs/ollama.log 2>&1 &"
else
    echo -e "  ${GREEN}✓${NC} Ollama running"
fi

echo ""
echo -e "${BLUE}[2/5] MCP Server 시작 중...${NC}"
nohup python3 mcp_server/mcp_server.py > logs/mcp_server.log 2>&1 &
MCP_PID=$!
echo $MCP_PID > .pids/mcp_server.pid
echo -e "  ${GREEN}✓${NC} MCP Server started (PID: $MCP_PID)"

sleep 2

echo ""
echo -e "${BLUE}[3/5] AI Agent 시작 중...${NC}"
nohup python3 agent/security_agent.py > logs/agent.log 2>&1 &
AGENT_PID=$!
echo $AGENT_PID > .pids/agent.pid
echo -e "  ${GREEN}✓${NC} AI Agent started (PID: $AGENT_PID)"

sleep 2

echo ""
echo -e "${BLUE}[4/5] FastAPI Backend 시작 중...${NC}"
nohup python3 api/main.py > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > .pids/api.pid
echo -e "  ${GREEN}✓${NC} FastAPI started (PID: $API_PID)"

sleep 2

echo ""
echo -e "${BLUE}[5/5] Flask Dashboard 시작 중...${NC}"
nohup python3 dashboard/app.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > .pids/dashboard.pid
echo -e "  ${GREEN}✓${NC} Flask Dashboard started (PID: $DASHBOARD_PID)"

sleep 2

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All services started!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}서비스 URL:${NC}"
echo -e "  📊 Dashboard: http://localhost:8080"
echo -e "  🔌 API:       http://localhost:8000"
echo ""
echo -e "${YELLOW}로그 확인:${NC}"
echo -e "  tail -f logs/mcp_server.log"
echo -e "  tail -f logs/agent.log"
echo -e "  tail -f logs/api.log"
echo -e "  tail -f logs/dashboard.log"
echo ""
echo -e "${YELLOW}정지:${NC}"
echo -e "  ./stop_all.sh"
echo ""
