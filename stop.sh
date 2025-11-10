#!/bin/bash
# stop.sh - 모든 서비스 정지

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🛑 서비스 정지 중...${NC}"
echo ""

STOPPED=0

# PID 파일로 정지
for service in mcp_server api dashboard; do
    pidfile=".pids/${service}.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "  ${RED}●${NC} Stopping ${service} (PID: $pid)..."
            kill $pid 2>/dev/null
            ((STOPPED++))
        fi
        rm "$pidfile"
    fi
done

# 프로세스 이름으로도 정지
pkill -f "suricata_server.py" 2>/dev/null && ((STOPPED++))
pkill -f "api/main.py" 2>/dev/null && ((STOPPED++))
pkill -f "dashboard/app.py" 2>/dev/null && ((STOPPED++))

echo ""
echo -e "${GREEN}✓ ${STOPPED}개 프로세스 정지 완료${NC}"
