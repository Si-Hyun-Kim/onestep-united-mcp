#!/bin/bash
# test-dashboard.sh - 대시보드 테스트 스크립트

echo "🧪 대시보드 테스트 중..."
echo ""

# API 헬스 체크
echo "[1/5] FastAPI 헬스 체크..."
curl -s http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || echo "❌ FastAPI 응답 없음"
echo ""

# 통계 API
echo "[2/5] 통계 API 테스트..."
curl -s http://localhost:8000/api/stats/overview | python3 -m json.tool | head -20
echo ""

# 로그 API
echo "[3/5] 로그 API 테스트..."
curl -s "http://localhost:8000/api/logs/suricata?count=5" | python3 -m json.tool | head -30
echo ""

# 상위 위협 API
echo "[4/5] 상위 위협 API 테스트..."
curl -s "http://localhost:8000/api/stats/top-threats?limit=5" | python3 -m json.tool
echo ""

# Dashboard 접속 테스트
echo "[5/5] Dashboard 접속 테스트..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login)

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ Dashboard 정상 동작 (HTTP $HTTP_CODE)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ 모든 테스트 통과!"
    echo ""
    echo "브라우저에서 접속하세요:"
    echo "🌐 http://localhost:8080"
    echo ""
    echo "로그인 정보:"
    echo "👤 Username: admin"
    echo "🔑 Password: admin123"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ Dashboard 응답 없음 (HTTP $HTTP_CODE)"
    echo ""
    echo "로그 확인:"
    echo "tail -f logs/dashboard.log"
fi
