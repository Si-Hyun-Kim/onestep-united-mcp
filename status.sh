#!/bin/bash
# status.sh - 서비스 상태 확인

echo "╔════════════════════════════════════════════════╗"
echo "║  📊 AI Security System Status                 ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check_service() {
    SERVICE=$1
    PIDFILE=".pids/$SERVICE.pid"
    PORT=$2
    
    echo -n "  $SERVICE: "
    
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 $PID 2>/dev/null; then
            echo -e "${GREEN}✓ Running${NC} (PID: $PID)"
            if [ ! -z "$PORT" ]; then
                if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
                    echo "    Port $PORT: ${GREEN}✓ Listening${NC}"
                fi
            fi
        else
            echo -e "${RED}✗ Not running${NC}"
        fi
    else
        echo -e "${RED}✗ Not running${NC}"
    fi
}

echo "서비스 상태:"
check_service "mcp_server" 9000
check_service "agent"
check_service "api" 8000
check_service "dashboard" 8080

echo ""
echo "시스템 의존성:"

echo -n "  Ollama: "
if pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
fi

echo -n "  Suricata: "
if pgrep -x "Suricata-Main" > /dev/null || sudo systemctl is-active suricata > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
fi

echo ""