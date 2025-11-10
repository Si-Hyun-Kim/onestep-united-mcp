#!/bin/bash
# start.sh - Suricata Security Monitoring System 시작
# 설치는 install.sh로 미리 완료되어 있어야 함

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
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

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo -e "  ${RED}✗${NC} Python 가상환경이 없습니다!"
    echo -e "  ${YELLOW}먼저 설치를 실행하세요: ./install.sh${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Python 가상환경 존재"

# 가상환경 활성화
source venv/bin/activate
echo -e "  ${GREEN}✓${NC} 가상환경 활성화됨"

# 필수 디렉토리 확인
for dir in mcp_server api dashboard logs; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} ${dir}/ 존재"
    else
        echo -e "  ${YELLOW}⚠${NC} ${dir}/ 없음 (생성)"
        mkdir -p "$dir"
    fi
done

# Suricata 확인
if command -v suricata &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Suricata 설치됨"
else
    echo -e "  ${RED}✗${NC} Suricata가 설치되지 않았습니다!"
    echo -e "  ${YELLOW}설치: sudo apt install suricata -y${NC}"
    exit 1
fi

# Suricata 실행 확인
if systemctl is-active --quiet suricata; then
    echo -e "  ${GREEN}✓${NC} Suricata 실행 중"
else
    echo -e "  ${YELLOW}⚠${NC} Suricata가 실행되지 않았습니다"
    read -p "지금 시작하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start suricata
        sleep 2
        echo -e "  ${GREEN}✓${NC} Suricata 시작됨"
    else
        echo -e "  ${RED}Suricata 없이는 로그를 수집할 수 없습니다.${NC}"
        exit 1
    fi
fi

# eve.json 읽기 권한 확인 (sudo로 확인해야 정확합니다)
if sudo [ -r "/var/log/suricata/eve.json" ]; then
    echo -e "  ${GREEN}✓${NC} eve.json (sudo) 읽기 가능"
else
    echo -e "  ${RED}✗${NC} eve.json (sudo) 읽기 권한 없음"
    echo -e "  ${YELLOW}권한 설정: ./fix-permissions.sh${NC}"
    exit 1
fi

echo ""

# ============================================
# 기존 프로세스 정리
# ============================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[정리] 기존 프로세스 확인 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# PID 파일 읽기
declare -A PIDS
if [ -f ".pids/mcp_server.pid" ]; then
    PIDS[mcp_server]=$(cat .pids/mcp_server.pid 2>/dev/null)
fi
if [ -f ".pids/api.pid" ]; then
    PIDS[api]=$(cat .pids/api.pid 2>/dev/null)
fi
if [ -f ".pids/dashboard.pid" ]; then
    PIDS[dashboard]=$(cat .pids/dashboard.pid 2>/dev/null)
fi

STOPPED_COUNT=0

for service in "${!PIDS[@]}"; do
    pid=${PIDS[$service]}
    if [ ! -z "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        echo -e "  ${YELLOW}⚠${NC} $service (PID: $pid) 실행 중 - 정지 중..."
        kill $pid 2>/dev/null
        ((STOPPED_COUNT++))
        sleep 1
    fi
done

if [ $STOPPED_COUNT -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} ${STOPPED_COUNT}개 프로세스 정리 완료"
else
    echo -e "  ${GREEN}✓${NC} 실행 중인 프로세스 없음"
fi

# 프로세스 이름으로도 정리
pkill -f "suricata_server.py" 2>/dev/null || true
pkill -f "api/main.py" 2>/dev/null || true
pkill -f "dashboard/app.py" 2>/dev/null || true

sleep 1
echo ""

# ============================================
# 서비스 시작
# ============================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[시작] 서비스 시작 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# PID 저장 디렉토리
mkdir -p .pids

# [1/4] MCP Server 시작 중...
echo -e "${GREEN}[▶ 1/4] MCP Server 시작 중...${NC}"

# [!!!] venv 안의 python3 절대 경로를 정의합니다.
VENV_PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"

if [ ! -f "mcp_server/suricata_server.py" ]; then
    echo -e "  ${RED}✗${NC} mcp_server/suricata_server.py 파일이 없습니다!"
    MCP_FAILED=true
else
    # [!!!] sudo로 venv의 python 경로를 명시하여 실행합니다.
    nohup sudo "$VENV_PYTHON_PATH" mcp_server/suricata_server.py > logs/mcp_server.log 2>&1 &
    MCP_PID=$!
    echo $MCP_PID > .pids/mcp_server.pid
    sleep 3
    
    # 로그 파일 확인으로 시작 여부 판단
    if grep -q "Suricata MCP Server started" logs/mcp_server.log 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} MCP Server 실행 중"
        # 실제 프로세스 PID 저장
        ACTUAL_PID=$(pgrep -f "suricata_server.py" | head -1)
        if [ ! -z "$ACTUAL_PID" ]; then
            echo $ACTUAL_PID > .pids/mcp_server.pid
        fi
    else
        # 추가 대기 후 프로세스 확인
        sleep 2
        if pgrep -f "suricata_server.py" > /dev/null; then
            echo -e "  ${GREEN}✓${NC} MCP Server 실행 확인됨"
            ACTUAL_PID=$(pgrep -f "suricata_server.py" | head -1)
            [ ! -z "$ACTUAL_PID" ] && echo $ACTUAL_PID > .pids/mcp_server.pid
        else
            echo -e "  ${RED}✗${NC} MCP Server 시작 실패"
            echo -e "  ${YELLOW}로그 확인: tail -f logs/mcp_server.log${NC}"
            MCP_FAILED=true
        fi
    fi
fi

echo ""
sleep 1

# [2/4] FastAPI Backend 시작
echo -e "${GREEN}[▶ 2/4] FastAPI Backend 시작 중...${NC}"

if [ ! -f "api/main.py" ]; then
    echo -e "  ${RED}✗${NC} api/main.py 파일이 없습니다!"
    API_FAILED=true
else
    nohup python3 api/main.py > logs/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > .pids/api.pid
    echo -e "  PID: ${API_PID}"
    sleep 2
    
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} FastAPI 실행 중"
        echo -e "  ${CYAN}URL: http://localhost:8000${NC}"
    else
        echo -e "  ${RED}✗${NC} FastAPI 시작 실패"
        echo -e "  ${YELLOW}로그 확인: tail -f logs/api.log${NC}"
        API_FAILED=true
    fi
fi

echo ""
sleep 1

# [3/4] Flask Dashboard 시작
echo -e "${GREEN}[▶ 3/4] Flask Dashboard 시작 중...${NC}"

if [ ! -f "dashboard/app.py" ]; then
    echo -e "  ${RED}✗${NC} dashboard/app.py 파일이 없습니다!"
    DASHBOARD_FAILED=true
else
    nohup python3 dashboard/app.py > logs/dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > .pids/dashboard.pid
    echo -e "  PID: ${DASHBOARD_PID}"
    sleep 2
    
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Flask Dashboard 실행 중"
        echo -e "  ${CYAN}URL: http://localhost:8080${NC}"
    else
        echo -e "  ${RED}✗${NC} Flask Dashboard 시작 실패"
        echo -e "  ${YELLOW}로그 확인: tail -f logs/dashboard.log${NC}"
        DASHBOARD_FAILED=true
    fi
fi

echo ""

# ============================================
# 상태 요약
# ============================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 서비스 상태 요약${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 각 서비스 상태 출력 (프로세스 이름으로 확인)
if [ -z "$MCP_FAILED" ] && pgrep -f "suricata_server.py" > /dev/null 2>&1; then
    ACTUAL_MCP_PID=$(pgrep -f "suricata_server.py" | head -1)
    echo -e "  MCP Server      : ${GREEN}● Running${NC} (PID: $ACTUAL_MCP_PID)"
else
    echo -e "  MCP Server      : ${RED}● Stopped${NC}"
fi

if [ -z "$API_FAILED" ] && [ ! -z "$API_PID" ] && ps -p $API_PID > /dev/null 2>&1; then
    echo -e "  FastAPI Backend : ${GREEN}● Running${NC} (PID: $API_PID)"
else
    echo -e "  FastAPI Backend : ${RED}● Stopped${NC}"
fi

if [ -z "$DASHBOARD_FAILED" ] && [ ! -z "$DASHBOARD_PID" ] && ps -p $DASHBOARD_PID > /dev/null 2>&1; then
    echo -e "  Flask Dashboard : ${GREEN}● Running${NC} (PID: $DASHBOARD_PID)"
else
    echo -e "  Flask Dashboard : ${RED}● Stopped${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🌐 접속 정보${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  대시보드        : ${GREEN}http://localhost:8080${NC}"
echo -e "  API 문서        : ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  로그인 정보     : ${YELLOW}admin / admin123${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📝 로그 확인${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  MCP Server      : ${YELLOW}tail -f logs/mcp_server.log${NC}"
echo -e "  FastAPI         : ${YELLOW}tail -f logs/api.log${NC}"
echo -e "  Dashboard       : ${YELLOW}tail -f logs/dashboard.log${NC}"
echo -e "  모든 로그       : ${YELLOW}tail -f logs/*.log${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}⚙️  제어 명령어${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  정지        : ${YELLOW}./stop.sh${NC}"
echo -e "  재시작      : ${YELLOW}./restart.sh${NC}"
echo -e "  상태 확인   : ${YELLOW}./status.sh${NC}"
echo ""

# 실패한 서비스가 있으면 경고
if [ ! -z "$MCP_FAILED" ] || [ ! -z "$API_FAILED" ] || [ ! -z "$DASHBOARD_FAILED" ]; then
    echo -e "${YELLOW}⚠️  일부 서비스가 시작하지 못했습니다.${NC}"
    echo -e "${YELLOW}   로그를 확인하여 문제를 해결하세요.${NC}"
    echo ""
fi

# 성공 메시지
if [ -z "$MCP_FAILED" ] && [ -z "$API_FAILED" ] && [ -z "$DASHBOARD_FAILED" ]; then
    echo -e "${GREEN}✅ 모든 서비스가 정상적으로 시작되었습니다!${NC}"
    echo ""
    echo -e "${GREEN}💡 브라우저에서 http://localhost:8080 을 열어보세요!${NC}"
    echo -e "${GREEN}   로그인: admin / admin123${NC}"
    echo ""
fi

# 실시간 로그 옵션
read -p "실시간 로그를 보시겠습니까? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📝 실시간 로그 (Ctrl+C로 종료)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    tail -f logs/*.log
fi
