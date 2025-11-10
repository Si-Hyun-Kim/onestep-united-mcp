# 🛡️ Suricata Security Monitoring System

**SIEM 스타일 실시간 보안 모니터링 대시보드**

Suricata IPS와 MCP 서버를 활용한 완전한 보안 모니터링 솔루션입니다.

---

## 🎯 주요 기능

### ✅ 현재 활성화

- ✅ **실시간 대시보드** - 24시간 통계, 차트, 상위 위협
- ✅ **로그 관리** - 조회, 검색, 필터링
- ✅ **룰 관리** - Suricata 룰 조회
- ✅ **IP 차단** - 원클릭 iptables 차단
- ✅ **사용자 인증** - 로그인/로그아웃

### 🚧 준비 중

- 🚧 **Red vs Blue** - HexStrike AI (Ollama 필요)
- 🚧 **AI 룰 생성** - Ollama 연동 후
- 🚧 **보고서** - PDF/HTML 생성

---

## 🚀 빠른 시작

```bash
# 1. 설치
./install.sh

# 2. 시작
./start.sh

# 3. 접속
# http://localhost:8080
# 로그인: admin / admin123
```

---

## 📡 접속 정보

| 서비스 | URL | 용도 |
|--------|-----|------|
| **대시보드** | http://localhost:8080 | 웹 UI |
| **API 문서** | http://localhost:8000/docs | Swagger UI |
| **로그인** | admin / admin123 | 기본 계정 |

---

## 🏗️ 아키텍처

```
브라우저 (8080)
    ↓
Flask Dashboard
    ↓
FastAPI Backend (8000)
    ↓
MCP Server
    ↓
Suricata IPS
```

---

## 📂 프로젝트 구조

```
security_project/
├── dashboard/          # Flask 웹 대시보드
│   ├── app.py
│   ├── templates/      # HTML 템플릿
│   └── static/         # CSS, JS
├── api/                # FastAPI 백엔드
│   └── main.py
├── mcp_server/         # MCP 서버
│   └── suricata_server.py
├── logs/               # 로그 파일
├── install.sh          # 설치 스크립트
├── start.sh            # 시작
├── stop.sh             # 정지
└── requirements.txt    # Python 패키지
```

---

## 🔧 스크립트

| 스크립트 | 설명 |
|----------|------|
| `./install.sh` | Suricata, Python 환경 설치 |
| `./start.sh` | 모든 서비스 시작 |
| `./stop.sh` | 모든 서비스 정지 |
| `./restart.sh` | 재시작 |
| `./status.sh` | 상태 확인 |
| `./fix-permissions.sh` | 권한 수정 |

---

## 📊 대시보드 기능

### 1. 메인 대시보드
- 통계 카드 (알림, 공격, 탐지율, 룰)
- 시간대별 알림 차트
- 심각도 분포 차트
- 상위 위협 IP (차단 기능)

### 2. 로그 관리
- Suricata 로그 조회
- 심각도 필터 (Critical/High/Medium/Low)
- 검색 (IP, 시그니처, 카테고리)
- 페이지네이션

### 3. 룰 관리
- 활성 Suricata 룰 조회
- 카테고리별 필터
- AI 생성 룰 구분

### 4. 보고서 (준비 중)
- PDF/HTML/JSON 생성
- Summary/Detailed/Executive 타입

### 5. Red vs Blue (비활성화)
- HexStrike AI 필요 (Ollama)

---

## 🔌 API 엔드포인트

### 통계
```bash
GET /api/stats/overview        # 전체 통계
GET /api/stats/timeline        # 시간대별
GET /api/stats/top-threats     # 상위 위협
```

### 로그
```bash
GET /api/logs/suricata         # 로그 조회
GET /api/logs/search?query=    # 검색
```

### 액션
```bash
POST /api/action/block-ip      # IP 차단
{
  "ip": "192.168.1.100",
  "reason": "Malicious"
}
```

---

## 🐛 문제 해결

### "Page not found"
```bash
./fix-permissions.sh
./restart.sh
```

### eve.json 읽기 오류
```bash
sudo chmod 644 /var/log/suricata/eve.json
sudo usermod -a -G adm $USER
# 로그아웃 후 재로그인
```

### FastAPI 시작 실패
```bash
tail -f logs/api.log
lsof -i :8000  # 포트 충돌 확인
```

### 로그 확인
```bash
tail -f logs/*.log              # 모든 로그
tail -f logs/dashboard.log      # Dashboard
tail -f logs/api.log            # API
tail -f logs/mcp_server.log     # MCP
```

---

## 🔐 보안 (프로덕션)

1. **SECRET_KEY 변경**
```bash
export SECRET_KEY="your-random-key"
```

2. **비밀번호 변경**
- dashboard/app.py의 USERS 수정

3. **HTTPS 사용**
- Nginx + Let's Encrypt

4. **방화벽**
```bash
sudo ufw allow 8080/tcp
```

---

## 📦 설치 상세

### 자동 (권장)
```bash
./install.sh
```

### 수동
```bash
# Suricata
sudo apt install suricata -y

# Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 권한
sudo usermod -a -G adm $USER
sudo chmod 644 /var/log/suricata/eve.json
```

---

## 📚 더 알아보기

- [Suricata 문서](https://suricata.readthedocs.io/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Flask 문서](https://flask.palletsprojects.com/)

---

## 💡 팁

- **더미 데이터**: FastAPI는 100개 더미 알림 자동 생성
- **HexStrike**: Ollama 설치 후 활성화 예정
- **로그**: `logs/` 디렉토리 확인

---

**버전:** 2.0.0  
**업데이트:** 2025-01-10  
**라이선스:** MIT
