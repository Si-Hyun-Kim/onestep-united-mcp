#!/bin/bash
# status.sh - 서비스 상태 확인

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 서비스 상태${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

check_service() {
    pidfile=".pids/${1}.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "  ${2}: ${GREEN}● Running${NC} (PID: $pid)"
            return 0
        fi
    fi
    echo -e "  ${2}: ${RED}● Stopped${NC}"
    return 1
}

# MCP Server는 프로세스 이름으로 확인
if pgrep -f "suricata_server.py" > /dev/null 2>&1; then
    MCP_PID=$(pgrep -f "suricata_server.py" | head -1)
    echo -e "  MCP Server     : ${GREEN}● Running${NC} (PID: $MCP_PID)"
else
    echo -e "  MCP Server     : ${RED}● Stopped${NC}"
fi

check_service "api" "FastAPI Backend"
check_service "dashboard" "Flask Dashboard"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🌐 URL${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Dashboard: ${GREEN}http://localhost:5000${NC}"
echo -e "  API Docs : ${GREEN}http://localhost:8000/docs${NC}"
echo ""
