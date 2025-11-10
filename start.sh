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
echo -e "  ${GREEN}✓${NC} venv 존재"

source venv/bin/activate
echo -e "  ${GREEN}✓${NC} venv 활성화"

command -v suricata &> /dev/null || { echo -e "  ${RED}✗${NC} Suricata 없음"; exit 1; }
echo -e "  ${GREEN}✓${NC} Suricata 설치됨"

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
for svc in api dashboard rule_generator; do
    [ -f ".pids/${svc}.pid" ] && {
        pid=$(cat ".pids/${svc}.pid" 2>/dev/null)
        [ ! -z "$pid" ] && ps -p $pid > /dev/null 2>&1 && {
            echo -e "  ${YELLOW}⚠${NC} ${svc} (PID: $pid) 정지 중..."
            kill $pid 2>/dev/null
            ((STOPPED++))
        }
    }
done

pkill -f "api/main.py" 2>/dev/null && ((STOPPED++))
pkill -f "dashboard/app.py" 2>/dev/null && ((STOPPED++))
pkill -f "rule_generator_service.py" 2>/dev/null && ((STOPPED++))

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

mkdir -p .pids

# [1/3] Rule Generator Service
echo -e "${GREEN}[▶ 1/3] Rule Generator (Ollama LLM)${NC}"

if [ ! -f "rule_generator_service.py" ]; then
    echo -e "  ${RED}✗${NC} rule_generator_service.py 없음!"
    RULE_GEN_FAILED=true
else
    nohup python3 rule_generator_service.py > logs/rule_generator.log 2>&1 &
    RULE_GEN_PID=$!
    echo $RULE_GEN_PID > .pids/rule_generator.pid
    echo -e "  PID: ${RULE_GEN_PID}"
    sleep 2
    
    if ps -p $RULE_GEN_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Rule Generator 실행 중"
        echo -e "  ${CYAN}URL: http://localhost:9000${NC}"
    else
        echo -e "  ${RED}✗${NC} 시작 실패"
        echo -e "  ${YELLOW}로그: tail -f logs/rule_generator.log${NC}"
        RULE_GEN_FAILED=true
    fi
fi

echo ""
sleep 1

# [2/3] FastAPI Backend
echo -e "${GREEN}[▶ 2/3] FastAPI Backend (+ Suricata Monitor)${NC}"

if [ ! -f "api/main.py" ]; then
    echo -e "  ${RED}✗${NC} api/main.py 없음!"
    API_FAILED=true
else
    nohup python3 api/main.py > logs/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > .pids/api.pid
    echo -e "  PID: ${API_PID}"
    sleep 3
    
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} FastAPI 실행 중"
        echo -e "  ${CYAN}URL: http://localhost:8000${NC}"
    else
        echo -e "  ${RED}✗${NC} 시작 실패"
        echo -e "  ${YELLOW}로그: tail -f logs/api.log${NC}"
        API_FAILED=true
    fi
fi

echo ""
sleep 1

# [3/3] Flask Dashboard
echo -e "${GREEN}[▶ 3/3] Flask Dashboard${NC}"

if [ ! -f "dashboard/app.py" ]; then
    echo -e "  ${RED}✗${NC} dashboard/app.py 없음!"
    DASHBOARD_FAILED=true
else
    nohup python3 dashboard/app.py > logs/dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > .pids/dashboard.pid
    echo -e "  PID: ${DASHBOARD_PID}"
    sleep 2
    
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Dashboard 실행 중"
        echo -e "  ${CYAN}URL: http://localhost:8080${NC}"
    else
        echo -e "  ${RED}✗${NC} 시작 실패"
        echo -e "  ${YELLOW}로그: tail -f logs/dashboard.log${NC}"
        DASHBOARD_FAILED=true
    fi
fi

echo ""

# ============================================
# 상태 요약
# ============================================

[ -z "$RULE_GEN_FAILED" ] && [ ! -z "$RULE_GEN_PID" ] && ps -p $RULE_GEN_PID > /dev/null 2>&1 && \
    echo -e "  Rule Generator  : ${GREEN}● Running${NC} (PID: $RULE_GEN_PID)" || \
    echo -e "  Rule Generator  : ${RED}● Stopped${NC}"

[ -z "$API_FAILED" ] && [ ! -z "$API_PID" ] && ps -p $API_PID > /dev/null 2>&1 && \
    echo -e "  FastAPI Backend : ${GREEN}● Running${NC} (PID: $API_PID)" || \
    echo -e "  FastAPI Backend : ${RED}● Stopped${NC}"

[ -z "$DASHBOARD_FAILED" ] && [ ! -z "$DASHBOARD_PID" ] && ps -p $DASHBOARD_PID > /dev/null 2>&1 && \
    echo -e "  Flask Dashboard : ${GREEN}● Running${NC} (PID: $DASHBOARD_PID)" || \
    echo -e "  Flask Dashboard : ${RED}● Stopped${NC}"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🌐 접속 정보${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  대시보드        : ${GREEN}http://localhost:8080${NC}"
echo -e "  API 문서        : ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  Rule Generator  : ${GREEN}http://localhost:9000${NC}"
echo -e "  로그인          : ${YELLOW}admin / admin123${NC}"
echo ""

[ -z "$RULE_GEN_FAILED" ] && [ -z "$API_FAILED" ] && [ -z "$DASHBOARD_FAILED" ] && {
    echo -e "${GREEN}✅ 모든 서비스 정상!${NC}"
    echo ""
    echo -e "${GREEN}💡 http://localhost:8080 을 열어보세요!${NC}"
    echo ""
}