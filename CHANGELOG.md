# 📋 변경 이력

## v2.0.0 (2025-01-10)

### ✨ 새로운 기능

- **Flask 웹 대시보드 추가**
  - SIEM 스타일 UI
  - 실시간 통계 대시보드
  - 로그 관리 (조회, 검색, 필터링)
  - 룰 관리
  - IP 차단 기능
  - 사용자 인증 (로그인/로그아웃)
  - 반응형 Bootstrap 5 디자인

- **FastAPI 백엔드 확장**
  - 대시보드용 API 엔드포인트 추가
  - 통계 API (/api/stats/*)
  - 로그 API (/api/logs/*)
  - 룰 관리 API
  - IP 차단 API
  - 100개 더미 데이터 자동 생성

- **MCP 서버 유지**
  - Suricata eve.json 실시간 파싱
  - FastMCP 기반

### 🚧 비활성화

- **HexStrike AI**
  - Red vs Blue 비교 분석 비활성화
  - Ollama 모델 선택 후 활성화 예정
  - UI에 준비 중 메시지 표시

- **MFA (Multi-Factor Authentication)**
  - 개발 환경에서 비활성화
  - 필요시 config.py에서 활성화 가능

### 🔧 개선사항

- 통합된 start.sh 스크립트
- Dashboard, API, MCP 서버 통합 관리
- 상세한 로그 출력
- 에러 핸들링 개선

### 📝 문서

- 통합 README.md
- API 문서 (Swagger UI)
- 문제 해결 가이드

## v1.0.0 (2025-01-09)

### 초기 릴리스

- MCP 서버 구현
- Suricata 로그 파싱
- 기본 통계 기능
