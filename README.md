# 🛡️ AI 기반 자동 보안 시스템

Suricata IPS와 HexStrike AI를 연동한 자동화된 보안 방어 시스템입니다.

## 🎯 주요 기능

### 1. **MCP 기반 로그 수집**
- Suricata IPS 로그 실시간 수집
- HexStrike AI 공격 로그 수집
- FastMCP 프로토콜 기반 통신

### 2. **AI 기반 분석 및 자동 대응**
- Ollama Qwen3 모델 사용
- 로그 패턴 분석 및 위협 탐지
- Suricata 룰 자동 생성
- IP 자동 차단

### 3. **SIEM 스타일 웹 대시보드**
- 실시간 로그 모니터링
- Red vs Blue 비교 분석
- 보고서 자동 생성
- MFA 인증 (Google Authenticator)

### 4. **Red Team vs Blue Team**
- HexStrike AI 공격 시뮬레이션
- Suricata IPS 방어 성능 측정
- 탐지율, False Positive 분석

---

## 📊 시스템 아키텍처

```
┌─────────────── Red Team 서버 ───────────────┐
│  HexStrike AI                               │
│  → 공격 로그 생성                            │
└────────────────┬────────────────────────────┘
                 │ SSH/rsync로 로그 전송
                 ↓
┌─────────────── Blue Team 서버 ──────────────┐
│  ┌──────────────────────────────────────┐  │
│  │  취약한 웹 서버 (테스트 대상)         │  │
│  │  - Frontend: 3000번 포트             │  │
│  │  - Backend:  5000번 포트             │  │
│  └──────────────────────────────────────┘  │
│            ↓                                │
│  ┌──────────────────────────────────────┐  │
│  │  Suricata IPS                        │  │
│  │  - 실시간 트래픽 모니터링             │  │
│  │  - /var/log/suricata/eve.json       │  │
│  └──────────────────────────────────────┘  │
│            ↓                                │
│  ┌──────────────────────────────────────┐  │
│  │  FastMCP Server (9000번 포트)        │  │
│  │  - Suricata & HexStrike 로그 수집    │  │
│  │  - 룰 관리 API                       │  │
│  └──────────────────────────────────────┘  │
│            ↓                                │
│  ┌──────────────────────────────────────┐  │
│  │  AI Agent (Ollama Qwen3)             │  │
│  │  - 로그 분석                         │  │
│  │  - 룰 자동 생성                       │  │
│  │  - IP 자동 차단                       │  │
│  └──────────────────────────────────────┘  │
│            ↓                                │
│  ┌──────────────────────────────────────┐  │
│  │  FastAPI Backend (8000번 포트)       │  │
│  │  - REST API                          │  │
│  │  - WebSocket                         │  │
│  └──────────────────────────────────────┘  │
│            ↓                                │
│  ┌──────────────────────────────────────┐  │
│  │  Flask Dashboard (8080번 포트)       │  │
│  │  - SIEM 대시보드                     │  │
│  │  - MFA 인증                          │  │
│  │  - 보고서 생성                        │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 🚀 빠른 시작

### 1. 시스템 요구사항

```bash
- Ubuntu 20.04+ / Debian 11+
- Python 3.10+
- Node.js 18+
- 최소 4GB RAM
- 10GB 디스크 공간
```

### 2. 한 번에 설치하기

```bash
# 1. 레포지토리 클론
git clone <your-repo>
cd security-automation

# 2. 자동 설치 (모든 의존성 포함)
chmod +x setup.sh
./setup.sh

# 설치되는 항목:
# - Python 3.10+ 및 필수 패키지
# - Node.js 18+
# - Suricata IPS
# - Ollama 및 Qwen3 모델
# - 모든 Python/Node 패키지
```

### 3. HexStrike AI 로그 연동 (Red Team 서버)

```bash
# Red Team 서버에서 실행
# 방법 1: rsync로 실시간 동기화
rsync -avz --progress /var/log/hexstrike/ \
  user@blue-team-ip:/path/to/security-automation/logs/hexstrike/

# 방법 2: SSH 마운트
sshfs user@blue-team-ip:/path/to/security-automation/logs/hexstrike \
  /local/mount/point
```

### 4. 시스템 시작

```bash
# 방법 1: 한 번에 시작
./start_all.sh

# 방법 2: 개별 시작
source venv/bin/activate

# Ollama 서버 (백그라운드)
nohup ollama serve > logs/ollama.log 2>&1 &

# MCP Server
python3 mcp_server/mcp_server.py

# AI Agent
python3 agent/security_agent.py

# FastAPI
python3 api/main.py

# Flask Dashboard
python3 dashboard/app.py
```

### 5. 대시보드 접속

```
http://localhost:8080

기본 계정:
- ID: admin
- Password: admin123
- MFA: 초기 로그인 후 설정
```

---

## 📖 상세 사용법

### 1. 대시보드 기능

#### **메인 대시보드**
- 실시간 통계 (24시간)
- 시간대별 알림 차트
- 심각도 분포 차트
- 상위 위협 IP 목록
- 원클릭 IP 차단

#### **로그 페이지**
```
http://localhost:8080/logs
```
- Suricata / HexStrike 로그 조회
- 심각도 필터링 (Critical/High/Medium/Low)
- 검색 기능
- 페이지네이션
- 로그 상세 정보

#### **룰 관리**
```
http://localhost:8080/rules
```
- 활성 Suricata 룰 목록
- 룰 추가/삭제
- 룰 유효성 검증
- AI 생성 룰 확인

#### **Red vs Blue 비교**
```
http://localhost:8080/analysis/comparison
```
- HexStrike 공격 vs Suricata 탐지
- 탐지율 (Detection Rate)
- False Positive/Negative
- IP 기반 상관관계 분석
- 시간대별 비교

#### **보고서 생성**
```
http://localhost:8080/reports
```
- 기간 설정 (시작/종료)
- 보고서 유형 선택
  * Summary: 요약 보고서
  * Detailed: 상세 보고서
  * Executive: 경영진용 보고서
- 포맷 선택 (PDF/HTML/JSON)
- 다운로드 및 저장

### 2. API 사용

#### **로그 조회**
```bash
# Suricata 최근 로그
curl http://localhost:8000/api/logs/suricata/recent?count=50

# HexStrike 최근 로그
curl http://localhost:8000/api/logs/hexstrike/recent?count=50

# 로그 검색
curl "http://localhost:8000/api/logs/search?query=SQL&source=all"
```

#### **IP 차단/해제**
```bash
# IP 차단
curl -X POST http://localhost:8000/api/action/block-ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "203.0.113.10", "reason": "Suspicious activity"}'

# IP 차단 해제
curl -X POST http://localhost:8000/api/action/unblock-ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "203.0.113.10"}'

# 차단된 IP 목록
curl http://localhost:8000/api/blocked-ips
```

#### **룰 관리**
```bash
# 활성 룰 조회
curl http://localhost:8000/api/rules/active

# 룰 추가
curl -X POST http://localhost:8000/api/rules/add \
  -H "Content-Type: application/json" \
  -d '{
    "rule_content": "alert tcp any any -> $HOME_NET 22 (msg:\"SSH Brute Force\"; threshold:type both,track by_src,count 5,seconds 60; sid:9000001; rev:1;)",
    "description": "SSH brute force detection"
  }'
```

#### **분석 API**
```bash
# Red vs Blue 비교
curl "http://localhost:8000/api/analysis/compare?time_window=60"

# 탐지 지표
curl "http://localhost:8000/api/analysis/detection-metrics?hours=24"
```

### 3. AI 에이전트 설정

```yaml
# agent/config.yaml

agent:
  name: "SecurityAgent"
  check_interval: 30  # 30초마다 분석

ollama:
  host: "http://localhost:11434"
  model: "qwen2.5:7b"
  temperature: 0.3  # 낮을수록 일관성 ↑
  max_tokens: 2000

detection:
  alert_threshold: 5  # IP당 알림 임계값
  time_window: 300    # 5분 시간 윈도우
  severity_weights:
    critical: 10
    high: 5
    medium: 2
    low: 1

auto_response:
  enabled: true       # 자동 차단 활성화
  block_threshold: 20 # 차단 점수 임계값
  whitelist:
    - "127.0.0.1"
    - "localhost"
    - "192.168.1.1"   # 신뢰하는 IP 추가
```

### 4. MFA 설정

```bash
# 1. 대시보드 로그인
http://localhost:8080/login

# 2. 우측 상단 프로필 → "MFA 설정"

# 3. QR 코드 스캔
#    - Google Authenticator (Android/iOS)
#    - Microsoft Authenticator
#    - Authy

# 4. 6자리 코드 입력하여 활성화

# 5. 다음 로그인부터 MFA 필수
```

---

## 🧪 테스트

### 1. HexStrike AI 공격 시뮬레이션

```bash
# Red Team 서버에서 실행
hexstrike attack --target http://blue-team-ip:3000 \
  --attack-type sql_injection \
  --count 10

hexstrike attack --target http://blue-team-ip:3000 \
  --attack-type xss \
  --count 5
```

### 2. 로그 확인

```bash
# Suricata 로그 실시간 모니터링
sudo tail -f /var/log/suricata/eve.json

# AI 에이전트 로그
tail -f logs/agent/actions.log

# 대시보드 로그
tail -f logs/dashboard/app.log
```

### 3. 탐지 성능 확인

```bash
# API로 탐지율 확인
curl http://localhost:8000/api/analysis/detection-metrics?hours=1

# 또는 대시보드에서
http://localhost:8080/analysis/comparison
```

---

## 🔧 문제 해결

### 1. Ollama 연결 실패

```bash
# Ollama 상태 확인
ollama list

# Ollama 시작
ollama serve

# 모델 재다운로드
ollama pull qwen2.5:7b
```

### 2. Suricata 로그 없음

```bash
# Suricata 상태 확인
sudo systemctl status suricata

# Suricata 시작
sudo systemctl start suricata

# 로그 파일 권한 확인
sudo chmod 644 /var/log/suricata/eve.json
```

### 3. MCP 서버 연결 실패

```bash
# 프로세스 확인
ps aux | grep mcp_server

# 로그 확인
tail -f logs/mcp_server.log

# 재시작
./restart_all.sh
```

### 4. 대시보드 로그인 불가

```bash
# Flask 로그 확인
tail -f logs/dashboard/app.log

# 비밀번호 재설정
# dashboard/app.py에서 USERS 딕셔너리 수정
```

---

## 📊 성능 및 리소스

### 시스템 리소스 사용량

| 컴포넌트 | CPU | 메모리 | 디스크 I/O |
|----------|-----|--------|------------|
| MCP Server | ~5% | ~100MB | 낮음 |
| AI Agent | ~15% | ~500MB | 중간 |
| Ollama | ~30% | ~2GB | 중간 |
| FastAPI | ~5% | ~150MB | 낮음 |
| Flask | ~5% | ~100MB | 낮음 |
| **총합** | ~60% | ~3GB | 중간 |

### 성능 최적화

```yaml
# agent/config.yaml에서 조정

# CPU/메모리 부족 시
agent:
  check_interval: 60  # 60초로 증가

ollama:
  model: "qwen2.5:3b"  # 더 작은 모델 사용
```

---

## 🔐 보안 권장사항

### 1. 프로덕션 배포 전

```bash
# 1. SECRET_KEY 변경
# .env 파일 수정
SECRET_KEY=<강력한-랜덤-키-생성>

# 2. 기본 비밀번호 변경
# dashboard/app.py의 USERS 수정

# 3. MFA 활성화 필수
MFA_ENABLED=True

# 4. HTTPS 설정
# Nginx 리버스 프록시 사용

# 5. 방화벽 설정
sudo ufw allow 8080/tcp  # Dashboard
sudo ufw allow 8000/tcp  # API (선택)
sudo ufw deny 9000/tcp   # MCP (외부 차단)
```

### 2. 화이트리스트 관리

```yaml
# agent/config.yaml
auto_response:
  whitelist:
    - "127.0.0.1"
    - "localhost"
    - "192.168.1.0/24"     # 내부 네트워크
    - "203.0.113.50"       # 신뢰하는 외부 IP
    - "YOUR_ADMIN_IP"      # 관리자 IP 필수!
```

---

## 📚 추가 자료

### 공식 문서
- [FastMCP 문서](https://github.com/modelcontextprotocol/mcp)
- [Suricata 문서](https://suricata.io/)
- [Ollama 문서](https://ollama.ai/)
- [HexStrike AI](https://hexstrike.ai/)

### 커뮤니티
- [Suricata Forum](https://forum.suricata.io/)
- [MCP Discord](https://discord.gg/modelcontextprotocol)

---

## 📝 라이선스

MIT License

---

## 🤝 기여

이슈 및 풀 리퀘스트 환영합니다!

---

## 📧 연락처

문제가 있으면 이슈를 생성해주세요.

---

**Happy Securing! 🛡️**