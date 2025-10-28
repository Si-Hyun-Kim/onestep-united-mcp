#!/bin/bash
# install.sh - One Step Security System 초기 설치 스크립트

set -e

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════╗
║                                               ║
║   🛡️  ONE STEP SECURITY SYSTEM 🛡️            ║
║                                               ║
║   Installation Script v2.0                   ║
║                                               ║
╚═══════════════════════════════════════════════╝
EOF
echo -e "${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}=== 설치 시작 ===${NC}"
echo ""

# 1. 시스템 체크
echo -e "${BLUE}[1/6] 시스템 검사 중...${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "  ${YELLOW}⚠${NC} $1 미설치"
        return 1
    fi
}

NEED_SUDO=false
MISSING_PACKAGES=()

if ! check_command python3; then
    MISSING_PACKAGES+=("python3")
    NEED_SUDO=true
fi

if ! check_command pip3; then
    MISSING_PACKAGES+=("python3-pip")
    NEED_SUDO=true
fi

if ! check_command curl; then
    MISSING_PACKAGES+=("curl")
    NEED_SUDO=true
fi

echo ""

# 2. sudo 권한
if [ "$NEED_SUDO" = true ]; then
    echo -e "${YELLOW}⚠️  sudo 권한이 필요합니다.${NC}"
    echo -e "   패키지: ${MISSING_PACKAGES[*]}"
    echo ""
    echo -e "${CYAN}🔐 sudo 비밀번호 입력:${NC}"
    sudo -v
    
    while true; do sudo -n true; sleep 50; kill -0 "$$" || exit; done 2>/dev/null &
    SUDO_KEEPER_PID=$!
fi

# 3. 기본 패키지
echo ""
echo -e "${BLUE}[2/6] 기본 패키지 설치...${NC}"

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    sudo apt update -qq
    for pkg in "${MISSING_PACKAGES[@]}"; do
        echo -e "  설치: ${pkg}"
        sudo apt install -y ${pkg} > /dev/null 2>&1
    done
    echo -e "  ${GREEN}✓${NC} 완료"
else
    echo -e "  ${GREEN}✓${NC} 모두 설치됨"
fi

echo -e "  ${GREEN}✓${NC} Python: $(python3 --version | awk '{print $2}')"
echo -e "  ${GREEN}✓${NC} pip3: $(pip3 --version | awk '{print $2}')"

# 4. Node.js (nvm)
echo ""
echo -e "${BLUE}[3/6] Node.js 설정...${NC}"

load_nvm() {
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
}

if command -v node &> /dev/null; then
    load_nvm 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Node.js: $(node -v)"
else
    if [ ! -d "$HOME/.nvm" ]; then
        echo -e "  ${CYAN}nvm 설치 중...${NC}"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    fi
    
    load_nvm
    echo -e "  ${CYAN}Node.js 24 설치 중...${NC}"
    nvm install 24
    nvm use 24
    nvm alias default 24
    echo -e "  ${GREEN}✓${NC} Node.js: $(node -v)"
fi

echo -e "  ${GREEN}✓${NC} npm: $(npm -v)"

# 5. Python 의존성
echo ""
echo -e "${BLUE}[4/6] Python 의존성...${NC}"

if python3 -c "import mcp" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} mcp 설치됨"
else
    echo -e "  ${CYAN}mcp 설치 중...${NC}"
    pip3 install mcp --user --break-system-packages 2>/dev/null || pip3 install mcp --user
    echo -e "  ${GREEN}✓${NC} mcp 설치 완료"
fi

# 6. Node.js 의존성
echo ""
echo -e "${BLUE}[5/6] Node.js 의존성...${NC}"

if [ ! -d "node_modules" ]; then
    npm install
    echo -e "  ${GREEN}✓${NC} npm install 완료"
else
    echo -e "  ${GREEN}✓${NC} node_modules 존재"
fi

# 7. 디렉토리 구조
echo ""
echo -e "${BLUE}[6/6] 프로젝트 구조...${NC}"

mkdir -p agent/logs agent/rules data logs .pids 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} 디렉토리 생성"

if [ ! -f "agent/agent_config.json" ]; then
    cat > agent/agent_config.json << 'EOF'
{
  "check_interval": 60,
  "alert_threshold": 5,
  "time_window": 300,
  "auto_block": true,
  "severity_weight": {"1": 10, "2": 5, "3": 2},
  "whitelist": ["127.0.0.1", "localhost"]
}
EOF
    echo -e "  ${GREEN}✓${NC} agent_config.json"
fi

# 완료
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 설치 완료!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}다음 단계:${NC}"
echo -e "  ${CYAN}source ~/.bashrc${NC}  # 또는 새 터미널"
echo -e "  ${CYAN}./start.sh${NC}        # 시작"
echo ""
echo -e "${BLUE}명령어: ./start.sh | ./stop.sh | ./restart.sh | ./status.sh${NC}"
echo ""

[ ! -z "$SUDO_KEEPER_PID" ] && kill $SUDO_KEEPER_PID 2>/dev/null || true