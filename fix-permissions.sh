#!/bin/bash
# fix-permissions.sh - Suricata 로그 권한 문제 해결

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🔧 Suricata 권한 설정${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# eve.json 확인
if [ ! -f "/var/log/suricata/eve.json" ]; then
    echo -e "  ${RED}✗${NC} /var/log/suricata/eve.json이 없습니다"
    echo -e "  ${YELLOW}Suricata를 시작하세요: sudo systemctl start suricata${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} eve.json 파일 존재"

# 읽기 권한 확인
if [ -r "/var/log/suricata/eve.json" ]; then
    echo -e "  ${GREEN}✓${NC} 이미 읽기 가능합니다"
    exit 0
fi

echo -e "  ${YELLOW}⚠${NC} 읽기 권한 없음, 설정 중..."
echo ""

# 방법 선택
echo -e "${YELLOW}권한 설정 방법:${NC}"
echo -e "  1) 파일 권한 변경 (chmod 644)"
echo -e "  2) 사용자를 adm 그룹에 추가"
echo -e "  3) 둘 다"
echo ""
read -p "선택 (1-3): " -n 1 -r
echo ""

case $REPLY in
    1)
        sudo chmod 644 /var/log/suricata/eve.json
        sudo chmod 755 /var/log/suricata
        echo -e "${GREEN}✓${NC} 파일 권한 변경 완료"
        ;;
    2)
        sudo usermod -a -G adm $(whoami)
        echo -e "${GREEN}✓${NC} adm 그룹 추가 완료"
        echo -e "${YELLOW}⚠${NC} 'newgrp adm' 실행 후 적용됩니다"
        ;;
    3)
        sudo chmod 644 /var/log/suricata/eve.json
        sudo chmod 755 /var/log/suricata
        sudo usermod -a -G adm $(whoami)
        echo -e "${GREEN}✓${NC} 모든 설정 완료"
        echo -e "${YELLOW}⚠${NC} 'newgrp adm' 실행 후 그룹 적용됩니다"
        ;;
    *)
        echo -e "${RED}취소됨${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓ 권한 설정 완료${NC}"
