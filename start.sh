#!/bin/bash
# start.sh - Suricata Security Monitoring System 시작 (통합 버전)

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 로고
echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     🚀 SURICATA SECURITY MONITORING SYSTEM 🚀         ║
║                                                       ║
║               Service Startup Script                  ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ============================================
# 사전 검사
# ============================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[사전 검사] 환경 확인 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

[ ! -d "venv" ] && echo -e "  ${RED}✗${NC} venv 없음" && exit 1
echo -e "  ${GREEN}✓${NC} venv"

source venv/bin/activate

command -v suricata &> /dev/null || { echo -e "  ${RED}✗${NC} Suricata 없음"; exit 1; }
echo -e "  ${GREEN}✓${NC} Suricata"

systemctl is-active --quiet suricata || {
    echo -e "  ${YELLOW}⚠${NC} Suricata 정지"
    read -p "시작? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && sudo systemctl start suricata && sleep 2
}
echo -e "  ${GREEN}✓${NC} Suricata 실행 중"
echo ""

# ============================================
# 기존 프로세스 정리
# ============================================

STOPPED=0
for svc in mcp api dashboard; do
    [ -f ".pids/${svc}.pid" ] && {
        pid=$(cat ".pids/${svc}.pid" 2>/dev/null)
        [ ! -z "$pid" ] && ps -p $pid > /dev/null 2>&1 && {
            kill $pid 2>/dev/null && ((STOPPED++))
        }
    }
done

pkill -f "mcp_server/suricata_server.py" 2>/dev/null && ((STOPPED++))
pkill -f "api/main.py" 2>/dev/null && ((STOPPED++))
pkill -f "dashboard/app.py" 2>/dev/null && ((STOPPED++))

[ $STOPPED -gt 0 ] && echo -e "  ${GREEN}✓${NC} ${STOPPED}개 정리" || echo -e "  ${GREEN}✓${NC} 없음"
sleep 1
echo ""


# ============================================
# 서비스 시작
# ============================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[시작] 서비스 시작 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p .pids logs data

# [1/3] MCP Server
echo -e "${GREEN}[▶ 1/3] MCP Server (Ollama 자동 룰 생성)${NC}"

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

if [ ! -f "mcp_server/suricata_server.py" ]; then
    echo -e "  ${RED}✗${NC} mcp_server/suricata_server.py 없음!"
    MCP_FAILED=true
else
    nohup sudo "$VENV_PYTHON" mcp_server/suricata_server.py > logs/mcp_server.log 2>&1 &
    sleep 3
    
    if pgrep -f "mcp_server/suricata_server.py" > /dev/null; then
        ACTUAL_PID=$(pgrep -f "mcp_server/suricata_server.py" | head -1)
        echo $ACTUAL_PID > .pids/mcp.pid
        echo -e "  ${GREEN}✓${NC} MCP Server 실행 중 (PID: $ACTUAL_PID)"
    else
        echo -e "  ${RED}✗${NC} 시작 실패"
        echo -e "  ${YELLOW}로그: tail -f logs/mcp_server.log${NC}"
        MCP_FAILED=true
    fi
fi

echo ""
sleep 1

# [2/3] FastAPI
echo -e "${GREEN}[▶ 2/3] FastAPI Backend${NC}"

if [ ! -f "api/main.py" ]; then
    echo -e "  ${RED}✗${NC} api/main.py 없음!"
    API_FAILED=true
else
    nohup python3 api/main.py > logs/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > .pids/api.pid
    sleep 3
    
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} FastAPI 실행 중 (PID: $API_PID)"
        echo -e "  ${CYAN}URL: http://localhost:8000${NC}"
    else
        echo -e "  ${RED}✗${NC} 시작 실패"
        API_FAILED=true
    fi
fi

echo ""
sleep 1

# [3/3] Dashboard
echo -e "${GREEN}[▶ 3/3] Flask Dashboard${NC}"

if [ ! -f "dashboard/app.py" ]; then
    echo -e "  ${RED}✗${NC} dashboard/app.py 없음!"
    DASHBOARD_FAILED=true
else
    nohup python3 dashboard/app.py > logs/dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > .pids/dashboard.pid
    sleep 2
    
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Dashboard 실행 중 (PID: $DASHBOARD_PID)"
        echo -e "  ${CYAN}URL: http://localhost:8080${NC}"
    else
        echo -e "  ${RED}✗${NC} 시작 실패"
        DASHBOARD_FAILED=true
    fi
fi

echo ""

# ============================================
# 상태 요약
# ============================================

pgrep -f "mcp_server/suricata_server.py" > /dev/null && \
    echo -e "  MCP Server : ${GREEN}● Running${NC}" || \
    echo -e "  MCP Server : ${RED}● Stopped${NC}"

[ -z "$API_FAILED" ] && ps -p $API_PID > /dev/null 2>&1 && \
    echo -e "  FastAPI    : ${GREEN}● Running${NC}" || \
    echo -e "  FastAPI    : ${RED}● Stopped${NC}"

[ -z "$DASHBOARD_FAILED" ] && ps -p $DASHBOARD_PID > /dev/null 2>&1 && \
    echo -e "  Dashboard  : ${GREEN}● Running${NC}" || \
    echo -e "  Dashboard  : ${RED}● Stopped${NC}"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🌐 접속 정보${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Dashboard : ${GREEN}http://localhost:8080${NC}"
echo -e "  API Docs  : ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  Login     : ${YELLOW}admin / admin123${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📁 데이터 파일${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  알림 데이터 : ${YELLOW}data/alerts.json${NC}"
echo -e "  생성 룰     : ${YELLOW}data/rules.json${NC}"
echo -e "  룰 파일     : ${YELLOW}/etc/suricata/rules/auto_generated.rules${NC}"
echo ""

[ -z "$MCP_FAILED" ] && [ -z "$API_FAILED" ] && [ -z "$DASHBOARD_FAILED" ] && {
    echo -e "${GREEN}✅ 모든 서비스 정상!${NC}"
    echo ""
}