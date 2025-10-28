#!/bin/bash
# setup.sh - 전체 시스템 자동 설치 스크립트

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  🛡️  AI Security Automation System Setup       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 현재 디렉토리
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}[1/10] 시스템 업데이트 확인 중...${NC}"
sudo apt update

echo ""
echo -e "${BLUE}[2/10] Python 확인 중...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "  ${YELLOW}Python3 설치 중...${NC}"
    sudo apt install -y python3 python3-pip python3-venv
fi
PYTHON_VERSION=$(python3 --version)
echo -e "  ${GREEN}✓${NC} $PYTHON_VERSION"

echo ""
echo -e "${BLUE}[3/10] Node.js 확인 중...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "  ${YELLOW}Node.js 설치 중...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi
NODE_VERSION=$(node --version)
echo -e "  ${GREEN}✓${NC} Node.js $NODE_VERSION"

echo ""
echo -e "${BLUE}[4/10] Suricata 확인 중...${NC}"
if ! command -v suricata &> /dev/null; then
    echo -e "  ${YELLOW}Suricata 설치 중...${NC}"
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:oisf/suricata-stable
    sudo apt update
    sudo apt install -y suricata
fi
SURICATA_VERSION=$(suricata --version | head -n1)
echo -e "  ${GREEN}✓${NC} $SURICATA_VERSION"

echo ""
echo -e "${BLUE}[5/10] Ollama 확인 중...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "  ${YELLOW}Ollama 설치 중...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
fi
echo -e "  ${GREEN}✓${NC} Ollama installed"

echo ""
echo -e "${BLUE}[6/10] Ollama 모델 다운로드 중...${NC}"
if ! ollama list | grep -q "qwen2.5:7b"; then
    echo -e "  ${YELLOW}Qwen2.5:7b 모델 다운로드 중... (시간이 걸릴 수 있습니다)${NC}"
    ollama pull qwen2.5:7b
fi
echo -e "  ${GREEN}✓${NC} qwen2.5:7b model ready"

echo ""
echo -e "${BLUE}[7/10] Python 가상환경 생성 중...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
else
    echo -e "  ${GREEN}✓${NC} Virtual environment exists"
fi

echo ""
echo -e "${BLUE}[8/10] Python 패키지 설치 중...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "  ${GREEN}✓${NC} Python packages installed"

echo ""
echo -e "${BLUE}[9/10] 디렉토리 구조 생성 중...${NC}"
mkdir -p logs/{suricata,hexstrike,agent,actions,dashboard}
mkdir -p rules/{custom,backup}
mkdir -p reports
mkdir -p data
echo -e "  ${GREEN}✓${NC} Directory structure created"

echo ""
echo -e "${BLUE}[10/10] 설정 파일 생성 중...${NC}"

# agent/config.yaml
if [ ! -f "agent/config.yaml" ]; then
    cat > agent/config.yaml << 'EOF'
agent:
  name: "SecurityAgent"
  check_interval: 30

ollama:
  host: "http://localhost:11434"
  model: "qwen2.5:7b"
  temperature: 0.3
  max_tokens: 2000

suricata:
  log_path: "/var/log/suricata/eve.json"
  rules_path: "/etc/suricata/rules"
  custom_rules_path: "./rules/custom/auto_generated.rules"

hexstrike:
  log_path: "./logs/hexstrike"

detection:
  alert_threshold: 5
  time_window: 300
  severity_weights:
    critical: 10
    high: 5
    medium: 2
    low: 1

auto_response:
  enabled: true
  block_threshold: 20
  whitelist:
    - "127.0.0.1"
    - "localhost"
EOF
    echo -e "  ${GREEN}✓${NC} agent/config.yaml created"
fi

# .env 파일 자동 생성
echo ""
echo -e "${BLUE}[8/10] .env 파일 생성 중...${NC}"

if [ -f ".env" ]; then
    echo -e "  ${YELLOW}⚠${NC} 기존 .env 파일 발견"
    BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
    cp .env "$BACKUP_FILE"
    echo -e "  ${GREEN}✓${NC} 백업 완료: $BACKUP_FILE"
fi

# SECRET_KEY 자동 생성
echo -e "  ${BLUE}→${NC} SECRET_KEY 자동 생성 중..."
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

cat > .env << EOF
# ============================================
# Flask 설정
# ============================================
SECRET_KEY=${SECRET_KEY}
FLASK_DEBUG=False
FLASK_ENV=production

# ============================================
# FastAPI Backend URL
# ============================================
API_URL=http://localhost:8000

# ============================================
# MFA (Multi-Factor Authentication)
# ============================================
MFA_ENABLED=True
MFA_ISSUER_NAME=Security Dashboard

# ============================================
# Logging
# ============================================
LOG_LEVEL=INFO

# ============================================
# Suricata 설정
# ============================================
SURICATA_LOG_PATH=/var/log/suricata/eve.json
SURICATA_RULES_PATH=/etc/suricata/rules

# ============================================
# HexStrike 설정
# ============================================
HEXSTRIKE_LOG_PATH=${SCRIPT_DIR}/logs/hexstrike

# ============================================
# Ollama 설정
# ============================================
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# ============================================
# Agent 설정
# ============================================
AGENT_CHECK_INTERVAL=30
AGENT_AUTO_BLOCK=True
AGENT_BLOCK_THRESHOLD=20

# ============================================
# 성능 설정
# ============================================
MAX_WORKERS=4
REQUEST_TIMEOUT=30

# ============================================
# 이메일 알림 (선택사항)
# ============================================
ENABLE_EMAIL_ALERTS=False
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# ALERT_EMAIL=admin@example.com

# ============================================
# Slack 알림 (선택사항)
# ============================================
ENABLE_SLACK_ALERTS=False
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# ============================================
# Telegram 알림 (선택사항)
# ============================================
ENABLE_TELEGRAM_ALERTS=False
# TELEGRAM_BOT_TOKEN=your-bot-token
# TELEGRAM_CHAT_ID=your-chat-id
EOF

chmod 600 .env 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} .env 파일 생성 완료 (SECRET_KEY 자동 생성)"

# .gitignore에 .env 추가
if [ ! -f ".gitignore" ]; then
    echo ".env" > .gitignore
    echo -e "  ${GREEN}✓${NC} .gitignore 생성 (.env 추가)"
elif ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo ".env" >> .gitignore
    echo -e "  ${GREEN}✓${NC} .gitignore에 .env 추가"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo -e "  1. Suricata 설정: sudo nano /etc/suricata/suricata.yaml"
echo -e "  2. Suricata 시작: sudo systemctl start suricata"
echo -e "  3. Ollama 시작: ollama serve"
echo -e "  4. 시스템 시작: ./start_all.sh"
echo ""