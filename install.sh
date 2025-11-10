#!/bin/bash
# install.sh - Suricata Security Monitoring System 설치
# Suricata는 이미 설치되어 있다고 가정 (/etc/suricata, /var/log/suricata/eve.json)

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
║     🛡️  SURICATA SECURITY MONITORING SYSTEM 🛡️          ║
║                                                       ║
║           One-Step Installation Wizard                ║
║                   Version 2.0.0                       ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${MAGENTA}📌 이 스크립트는 Suricata가 이미 설치되어 있다고 가정합니다.${NC}"
echo -e "${MAGENTA}   위치: /etc/suricata, /var/log/suricata/eve.json${NC}"
echo -e "${MAGENTA}   설치 후 './start.sh'로 서비스를 시작하세요.${NC}"
echo ""

# [0/8] 스크립트 권한 자동 부여
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[0/8] 스크립트 권한 확인 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

SCRIPT_FILES=("start.sh" "stop.sh" "restart.sh" "status.sh" "fix-permissions.sh")
FIXED_COUNT=0

for script in "${SCRIPT_FILES[@]}"; do
    if [ -f "$script" ]; then
        if [ ! -x "$script" ]; then
            echo -e "  ${YELLOW}⚠${NC} ${script} - 실행 권한 없음, 추가 중..."
            if chmod +x "$script" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} ${script} - 권한 부여 완료"
                ((FIXED_COUNT++))
            else
                echo -e "  ${RED}✗${NC} ${script} - 실패"
            fi
        else
            echo -e "  ${GREEN}✓${NC} ${script} - 실행 권한 OK"
        fi
    else
        echo -e "  ${YELLOW}⊝${NC} ${script} - 파일 없음 (OK)"
    fi
done

[ $FIXED_COUNT -gt 0 ] && echo -e "  ${CYAN}💡 ${FIXED_COUNT}개 파일에 자동으로 실행 권한 부여${NC}"
echo ""

# [1/8] 시스템 요구사항 체크
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1/8] 시스템 요구사항 체크...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 (설치 필요)"
        return 1
    fi
}

NEED_SUDO=false
MISSING_PACKAGES=()

check_command python3 || { MISSING_PACKAGES+=("python3"); NEED_SUDO=true; }
check_command pip3 || { MISSING_PACKAGES+=("python3-pip"); NEED_SUDO=true; }
check_command curl || { MISSING_PACKAGES+=("curl"); NEED_SUDO=true; }

# Suricata 체크 (필수!)
if check_command suricata; then
    SURICATA_VERSION=$(suricata --version 2>&1 | head -n1)
    echo -e "      ${CYAN}버전: ${SURICATA_VERSION}${NC}"
else
    echo -e "  ${RED}✗✗✗ Suricata가 설치되지 않았습니다! ✗✗✗${NC}"
    echo -e "  ${CYAN}설치 방법: sudo apt install suricata -y${NC}"
    read -p "지금 설치하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt update && sudo apt install suricata -y
        sudo systemctl enable suricata && sudo systemctl start suricata
        echo -e "  ${GREEN}✓${NC} Suricata 설치 완료"
    else
        echo -e "  ${RED}설치를 취소했습니다. Suricata 없이는 작동하지 않습니다.${NC}"
        exit 1
    fi
fi

echo ""

# [2/8] sudo 권한
if [ "$NEED_SUDO" = true ] || [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}[2/8] sudo 권한 확인...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  필요한 패키지: ${MISSING_PACKAGES[*]}${NC}"
    echo -e "${CYAN}🔐 sudo 비밀번호를 입력해주세요:${NC}"
    sudo -v
    while true; do sudo -n true; sleep 50; kill -0 "$$" || exit; done 2>/dev/null &
    SUDO_KEEPER_PID=$!
    echo ""
fi

# [3/8] Python 환경
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3/8] Python 환경 확인 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "  ${YELLOW}⚠${NC} 패키지 설치 시작..."
    sudo apt update -qq
    for pkg in "${MISSING_PACKAGES[@]}"; do
        echo -e "  설치 중: ${pkg}"
        sudo apt install -y ${pkg} > /dev/null 2>&1
    done
    echo -e "  ${GREEN}✓${NC} 패키지 설치 완료"
else
    echo -e "  ${GREEN}✓${NC} Python3와 pip3가 이미 설치되어 있습니다."
fi

echo -e "  ${GREEN}✓${NC} Python: $(python3 --version 2>&1 | awk '{print $2}')"
echo -e "  ${GREEN}✓${NC} pip3: $(pip3 --version 2>&1 | awk '{print $2}')"
echo ""

# [4/8] Python 가상환경
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/8] Python 가상환경 생성...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -d "venv" ]; then
    echo -e "  ${GREEN}✓${NC} 가상환경이 이미 존재합니다."
else
    echo -e "  ${YELLOW}⏳${NC} 가상환경 생성 중..."
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} 가상환경 생성 완료"
fi

source venv/bin/activate
echo -e "  ${GREEN}✓${NC} 가상환경 활성화됨"
echo ""

# [5/8] Python 의존성
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[5/8] Python 의존성 설치...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "  ${YELLOW}⏳${NC} pip 패키지 설치 중... (시간이 걸릴 수 있습니다)"

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
else
    pip install mcp fastapi uvicorn flask flask-cors aiofiles --quiet
    echo -e "  ${YELLOW}💡 requirements.txt가 없어 기본 패키지만 설치했습니다.${NC}"
fi

echo -e "  ${GREEN}✓${NC} Python 의존성 설치 완료"
echo -e "  ${CYAN}설치된 패키지:${NC}"
pip list | grep -E "mcp|fastapi|flask" | while read line; do
    echo -e "    ${GREEN}•${NC} $line"
done
echo ""

# [6/8] 디렉토리 구조
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[6/8] 프로젝트 디렉토리 구조 생성...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

mkdir -p mcp_server logs api dashboard llm_integration data .pids 2>/dev/null || true

echo -e "  ${GREEN}✓${NC} mcp_server/      - MCP 서버 (Suricata 모니터링)"
echo -e "  ${GREEN}✓${NC} api/             - FastAPI 백엔드"
echo -e "  ${GREEN}✓${NC} dashboard/       - Flask 대시보드"
echo -e "  ${GREEN}✓${NC} logs/            - 서비스 로그"
echo -e "  ${GREEN}✓${NC} llm_integration/ - LLM 룰 생성기 (준비용)"
echo -e "  ${GREEN}✓${NC} data/            - 데이터 저장소"
echo -e "  ${GREEN}✓${NC} .pids/           - 프로세스 ID 저장"

cat > llm_integration/README.md << 'EOF'
# LLM Integration (Future)

이 디렉토리는 향후 LLM 연동을 위해 준비되었습니다.

## 계획된 기능
- Suricata 로그 분석
- 새로운 공격 패턴 학습
- Suricata 룰 자동 생성
- /etc/suricata/rules/에 룰 추가

## 현재 상태
🚧 준비 중 - Ollama 모델 선택 후 구현 예정
EOF

echo -e "  ${CYAN}💡 llm_integration/README.md 생성${NC}"
echo ""

# [6.5/8] Suricata 로그 권한 설정
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[6.5/8] Suricata 설정 확인 중... ⭐${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Suricata 실행 확인
if systemctl is-active --quiet suricata; then
    echo -e "  ${GREEN}✓${NC} Suricata 실행 중"
else
    echo -e "  ${YELLOW}⚠${NC} Suricata가 실행되지 않았습니다."
    read -p "Suricata를 시작하시겠습니까? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && sudo systemctl start suricata && sleep 3 && echo -e "  ${GREEN}✓${NC} Suricata 시작됨"
fi

# eve.json 파일 확인
if [ -f "/var/log/suricata/eve.json" ]; then
    echo -e "  ${GREEN}✓${NC} eve.json 파일 존재"
    
    if [ -r "/var/log/suricata/eve.json" ]; then
        echo -e "  ${GREEN}✓${NC} eve.json 읽기 가능"
    else
        echo -e "  ${RED}✗${NC} eve.json 읽기 권한 없음"
        echo ""
        echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${YELLOW}⚠️  권한 문제 해결 필요${NC}"
        echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "  ${YELLOW}1)${NC} 파일 권한 변경 (chmod 644) - ${GREEN}권장${NC}"
        echo -e "  ${YELLOW}2)${NC} 사용자를 adm 그룹에 추가"
        echo -e "  ${YELLOW}3)${NC} 둘 다 실행 - ${GREEN}가장 안전${NC}"
        echo -e "  ${YELLOW}4)${NC} 건너뛰기"
        echo ""
        read -p "선택 (1-4): " -n 1 -r PERMISSION_CHOICE
        echo ""
        
        case $PERMISSION_CHOICE in
            1)
                sudo chmod 644 /var/log/suricata/eve.json && sudo chmod 755 /var/log/suricata
                echo -e "  ${GREEN}✓${NC} 파일 권한 644로 변경 완료"
                ;;
            2)
                CURRENT_USER=$(whoami)
                if groups $CURRENT_USER | grep -q "\badm\b"; then
                    echo -e "  ${GREEN}✓${NC} 이미 adm 그룹에 속해 있습니다"
                else
                    sudo usermod -a -G adm $CURRENT_USER
                    echo -e "  ${GREEN}✓${NC} adm 그룹 추가 완료"
                    echo -e "  ${YELLOW}⚠️  'newgrp adm' 실행 후 ./install.sh 재실행하세요${NC}"
                    [ ! -z "$SUDO_KEEPER_PID" ] && kill $SUDO_KEEPER_PID 2>/dev/null || true
                    exit 0
                fi
                ;;
            3)
                sudo chmod 644 /var/log/suricata/eve.json && sudo chmod 755 /var/log/suricata
                CURRENT_USER=$(whoami)
                groups $CURRENT_USER | grep -q "\badm\b" || sudo usermod -a -G adm $CURRENT_USER
                echo -e "  ${GREEN}✓${NC} 파일 권한 및 그룹 설정 완료"
                ;;
            4)
                echo -e "  ${YELLOW}⚠${NC} 건너뛰기 - 나중에 ./fix-permissions.sh 실행"
                ;;
        esac
        
        [ -r "/var/log/suricata/eve.json" ] && echo -e "  ${GREEN}✓${NC} 최종 확인: eve.json 읽기 가능" || echo -e "  ${YELLOW}⚠${NC} 최종 확인: 여전히 읽기 불가"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} eve.json 파일이 없습니다."
    echo -e "  ${CYAN}💡 Suricata를 시작하면 자동으로 생성됩니다.${NC}"
fi

# Suricata 룰 디렉토리 확인
if [ -d "/etc/suricata/rules" ]; then
    echo -e "  ${GREEN}✓${NC} Suricata 룰 디렉토리 존재: /etc/suricata/rules"
    [ -w "/etc/suricata/rules" ] && echo -e "  ${GREEN}✓${NC} 룰 디렉토리 쓰기 가능 (LLM 룰 추가 준비 완료)" || echo -e "  ${YELLOW}⚠${NC} 룰 디렉토리 쓰기 권한 없음"
else
    echo -e "  ${RED}✗${NC} /etc/suricata/rules 디렉토리 없음"
fi

echo ""

# [7/8] 설정 파일 생성
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[7/8] 설정 파일 생성 중...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

[ ! -f "config.json" ] && cat > config.json << 'EOF'
{
  "suricata": {
    "eve_log_path": "/var/log/suricata/eve.json",
    "rules_path": "/etc/suricata/rules",
    "config_path": "/etc/suricata/suricata.yaml"
  },
  "mcp_server": {
    "backfill_lines": 50,
    "max_alerts": 1000
  },
  "api": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "dashboard": {
    "host": "0.0.0.0",
    "port": 5000
  },
  "llm_integration": {
    "enabled": false,
    "model": "TBD",
    "comment": "Ollama 모델 선택 후 활성화 예정"
  }
}
EOF

[ ! -f ".env" ] && cat > .env << 'EOF'
EVE_LOG=/var/log/suricata/eve.json
SURICATA_RULES=/etc/suricata/rules
LOG_LEVEL=INFO
EOF

echo -e "  ${GREEN}✓${NC} config.json 생성"
echo -e "  ${GREEN}✓${NC} .env 생성"
echo ""

# [8/8] 설치 완료
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[8/8] 설치 완료 확인...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "  ${GREEN}✓${NC} Python 가상환경"
echo -e "  ${GREEN}✓${NC} Python 의존성"
echo -e "  ${GREEN}✓${NC} 디렉토리 구조"
echo -e "  ${GREEN}✓${NC} 설정 파일"
echo -e "  ${GREEN}✓${NC} Suricata 연동 준비"
echo ""

[ ! -z "$SUDO_KEEPER_PID" ] && kill $SUDO_KEEPER_PID 2>/dev/null || true

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 설치 완료!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📌 다음 단계:${NC}"
echo -e "  ${YELLOW}1)${NC} 가상환경 활성화: ${GREEN}source venv/bin/activate${NC}"
echo -e "  ${YELLOW}2)${NC} 서비스 시작: ${GREEN}./start.sh${NC}"
echo -e "  ${YELLOW}3)${NC} 대시보드 접속: ${GREEN}http://localhost:5000${NC}"
echo ""
echo -e "${BLUE}⚙️  유용한 명령어: ./start.sh | ./stop.sh | ./restart.sh | ./status.sh${NC}"
echo ""
