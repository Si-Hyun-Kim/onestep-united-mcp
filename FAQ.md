# ❓ 자주 묻는 질문 (FAQ)

## 📖 목차

1. [일반 질문](#일반-질문)
2. [설치 및 설정](#설치-및-설정)
3. [사용법](#사용법)
4. [성능 및 최적화](#성능-및-최적화)
5. [트러블슈팅](#트러블슈팅)
6. [보안](#보안)

---

## 일반 질문

### Q1. 이 시스템은 무엇인가요?

**A:** AI 기반 자동 보안 시스템으로, Suricata IPS와 HexStrike AI를 연동하여 실시간으로 공격을 탐지하고 자동으로 대응합니다. Ollama Qwen3 AI 모델을 사용하여 로그를 분석하고 최적의 방화벽 룰을 자동 생성합니다.

**주요 기능:**
- ✅ 실시간 로그 모니터링 (Suricata IPS, HexStrike AI)
- ✅ AI 기반 로그 분석 (Ollama Qwen3)
- ✅ 자동 룰 생성 및 IP 차단
- ✅ SIEM 스타일 웹 대시보드
- ✅ Red vs Blue 비교 분석
- ✅ 자동 보고서 생성

---

### Q2. 실제 프로덕션 환경에서 사용할 수 있나요?

**A:** 네! 하지만 다음 사항을 반드시 확인하세요:

✅ **필수 조치:**
1. 기본 비밀번호 변경
2. SECRET_KEY 변경
3. MFA 활성화
4. HTTPS 설정
5. 방화벽 설정
6. 화이트리스트에 관리자 IP 추가
7. 정기 백업 설정

⚠️ **주의사항:**
- 테스트 환경에서 충분히 검증 후 사용
- 화이트리스트에 본인 IP 추가 (차단 방지)
- 중요한 서버에 바로 적용하지 말 것

---

### Q3. 비용이 얼마나 드나요?

**A:** 오픈소스 프로젝트로 **무료**입니다!

**필요한 비용:**
- 서버 호스팅 비용 (AWS, GCP, Azure 등)
- 도메인 비용 (선택사항)
- SSL 인증서 (Let's Encrypt 무료)

**권장 서버 사양:**
- 최소: 4GB RAM, 2 Core CPU (~$20-40/월)
- 권장: 8GB RAM, 4 Core CPU (~$40-80/월)

---

## 설치 및 설정

### Q4. 설치가 어렵나요?

**A:** 전혀! 자동 설치 스크립트를 제공합니다:

```bash
# 단 3단계!
git clone <your-repo>
cd security-automation
./setup.sh  # 모든 것을 자동 설치

# 시작
./start_all.sh
```

**설치되는 항목:**
- Python 3.10+ 및 패키지
- Node.js 및 패키지
- Suricata IPS
- Ollama + Qwen3 모델
- 모든 필요한 의존성

---

### Q5. Windows에서 실행할 수 있나요?

**A:** 직접 실행은 어렵지만, 다음 방법들이 있습니다:

**방법 1: WSL2 (권장)**
```powershell
# WSL2 설치
wsl --install

# Ubuntu 실행
wsl

# 설치 진행
git clone <repo>
cd security-automation
./setup.sh
```

**방법 2: Docker**
```bash
docker-compose up -d
```

**방법 3: VM (VirtualBox, VMware)**
- Ubuntu 20.04 VM 생성
- 위의 일반 설치 절차 진행

---

### Q6. HexStrike AI가 없으면 사용할 수 없나요?

**A:** 아니요! HexStrike 없이도 사용 가능합니다:

**Suricata만 사용:**
- 실제 트래픽 모니터링
- IPS 로그 분석
- 자동 룰 생성
- AI 기반 분석

**Red Team이 없을 때:**
- 실제 공격 로그 사용
- 다른 공격 시뮬레이터 사용 (Metasploit, Burp Suite 등)
- 샘플 로그로 테스트

---

## 사용법

### Q7. 대시보드에 처음 로그인할 때 MFA를 어떻게 설정하나요?

**A:** 단계별 가이드:

```bash
# 1. 기본 로그인
ID: admin
Password: admin123  # 변경하세요!

# 2. 우측 상단 프로필 클릭 → "MFA 설정"

# 3. QR 코드 스캔
- Google Authenticator (Android/iOS)
- Microsoft Authenticator
- Authy

# 4. 6자리 코드 입력하여 활성화

# 5. 다음 로그인부터 MFA 필수
```

**QR 코드 스캔이 안 될 때:**
- 시크릿 키를 수동으로 입력
- 시크릿 키는 QR 코드 아래에 표시됨

---

### Q8. IP를 차단했는데 해제하려면 어떻게 하나요?

**A:** 여러 방법이 있습니다:

**방법 1: 대시보드 (권장)**
```
1. 대시보드 → 설정 → 차단된 IP
2. 해당 IP 찾기
3. "차단 해제" 버튼 클릭
```

**방법 2: API**
```bash
curl -X POST http://localhost:8000/api/action/unblock-ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "203.0.113.10"}'
```

**방법 3: 직접 (긴급 시)**
```bash
# 차단된 IP 확인
sudo iptables -L INPUT -n | grep DROP

# 차단 해제
sudo iptables -D INPUT -s 203.0.113.10 -j DROP
```

---

### Q9. 보고서는 어떻게 생성하나요?

**A:** 대시보드에서 간단히 생성:

```
1. 대시보드 → 보고서 → 보고서 생성

2. 기간 설정
   - 시작 날짜/시간
   - 종료 날짜/시간

3. 보고서 유형 선택
   - Summary: 요약 보고서
   - Detailed: 상세 보고서
   - Executive: 경영진용 보고서

4. 포맷 선택
   - PDF (권장)
   - HTML
   - JSON

5. "생성" 클릭

6. 다운로드
```

**자동 보고서 생성 (고급):**
```python
# 매일 오전 9시 보고서 자동 생성
# crontab -e
0 9 * * * /path/to/generate_daily_report.sh
```

---

### Q10. Red vs Blue 비교는 무엇인가요?

**A:** HexStrike AI 공격과 Suricata IPS 탐지를 비교 분석합니다:

**비교 항목:**
- ✅ 총 공격 수 (Red Team)
- ✅ 총 탐지 수 (Blue Team)
- ✅ 탐지율 (%)
- ✅ 매칭된 공격 (정상 탐지)
- ✅ 미탐지 공격 (False Negative)
- ✅ 오탐 (False Positive)

**활용 방법:**
1. 방어 성능 평가
2. 룰 최적화 필요성 판단
3. 보안 격차 식별
4. 개선 방향 수립

---

## 성능 및 최적화

### Q11. 시스템이 느린데 어떻게 최적화하나요?

**A:** 단계별 최적화 방법:

**1단계: Ollama 모델 변경**
```bash
# 현재: qwen2.5:7b (4GB RAM)
# 변경: qwen2.5:3b (2GB RAM)

ollama pull qwen2.5:3b

# agent/config.yaml 수정
ollama:
  model: "qwen2.5:3b"

# 재시작
sudo systemctl restart security-agent
```

**2단계: 체크 주기 조정**
```yaml
# agent/config.yaml
agent:
  check_interval: 60  # 60초로 증가 (기본: 30초)
```

**3단계: 로그 개수 제한**
```python
# mcp_server/log_collectors.py
async def get_recent_logs(self, count: int = 50):  # 100 → 50으로 감소
```

**4단계: 캐싱 활용**
```bash
# Redis 설치 및 사용
sudo apt install redis-server
```

---

### Q12. 메모리가 부족해요!

**A:** 메모리 절약 팁:

**즉시 조치:**
```bash
# 1. Ollama 모델 변경 (4GB → 2GB)
ollama pull qwen2.5:3b

# 2. 불필요한 서비스 정지
sudo systemctl stop security-agent  # AI 분석 일시 정지
```

**영구 조치:**
```yaml
# agent/config.yaml
agent:
  check_interval: 120  # 2분마다 (메모리 절약)

ollama:
  model: "qwen2.5:3b"  # 작은 모델
```

**하드웨어 업그레이드:**
- 최소 4GB → 권장 8GB RAM
- SSD 사용 (속도 향상)

---

## 트러블슈팅

### Q13. "Ollama 서버에 연결할 수 없습니다" 오류

**A:** 해결 방법:

```bash
# 1. Ollama 실행 확인
pgrep -x ollama

# 없으면 시작
ollama serve

# 또는 백그라운드 실행
nohup ollama serve > logs/ollama.log 2>&1 &

# 2. 포트 확인
netstat -tlnp | grep 11434

# 3. 방화벽 확인
sudo ufw status

# 11434 포트 열기
sudo ufw allow 11434/tcp

# 4. 테스트
curl http://localhost:11434/api/tags
```

---

### Q14. 실수로 제 IP를 차단했어요!

**A:** 긴급 복구 방법:

**방법 1: 콘솔 접속 (클라우드)**
```bash
# AWS, GCP 등 콘솔에서 접속
sudo iptables -D INPUT -s YOUR_IP -j DROP
```

**방법 2: 다른 서버에서**
```bash
# SSH로 접속 가능하면
ssh user@server-ip
sudo iptables -D INPUT -s YOUR_IP -j DROP
```

**방법 3: 재부팅** (iptables 규칙은 재부팅 시 초기화됨)
```bash
sudo reboot
```

**예방 조치:**
```yaml
# agent/config.yaml - 화이트리스트에 추가!
auto_response:
  whitelist:
    - "YOUR_IP_ADDRESS"  # 필수!
```

---

### Q15. Suricata 로그가 보이지 않아요

**A:** 체크리스트:

```bash
# 1. Suricata 실행 확인
sudo systemctl status suricata

# 안 돌고 있으면
sudo systemctl start suricata

# 2. 로그 파일 확인
ls -la /var/log/suricata/eve.json

# 3. 권한 확인
sudo chmod 644 /var/log/suricata/eve.json

# 4. 로그 생성 확인
sudo tail -f /var/log/suricata/eve.json

# 5. 트래픽 확인 (로그가 안 생기면 트래픽이 없는 것)
# 테스트 트래픽 생성
curl http://testmynids.org/uid/index.html

# 6. 설정 확인
sudo nano /etc/suricata/suricata.yaml
# eve-log:
#   enabled: yes
```

---

## 보안

### Q16. 이 시스템은 안전한가요?

**A:** 보안 모범 사례를 따르면 안전합니다:

**기본 보안:**
- ✅ MFA 인증
- ✅ HTTPS (Let's Encrypt)
- ✅ 세션 관리
- ✅ Rate Limiting

**권장 조치:**
1. **강력한 비밀번호 사용**
2. **정기 업데이트**
3. **로그 모니터링**
4. **정기 보안 감사**
5. **최소 권한 원칙**

**취약점 신고:**
security@your-domain.com

---

### Q17. 대시보드를 인터넷에 공개해도 되나요?

**A:** 가능하지만, 반드시 다음을 설정하세요:

**필수 조치:**
```nginx
# Nginx에서 IP 제한
location / {
    allow YOUR_OFFICE_IP;
    allow YOUR_HOME_IP;
    deny all;
    
    proxy_pass http://127.0.0.1:8080;
}
```

**추가 보안:**
- VPN 사용 권장
- Fail2ban 설정
- CloudFlare 사용

**내부망만 사용 (가장 안전):**
```bash
# 외부 접근 차단
sudo ufw deny 8080/tcp
```

---

### Q18. 로그에 민감한 정보가 있나요?

**A:** 네, 로그에는 다음이 포함될 수 있습니다:

**민감 정보:**
- IP 주소
- 공격 패턴
- 시스템 정보
- 네트워크 구성

**보호 방법:**
1. **로그 암호화**
2. **접근 제한**
3. **정기 삭제**
4. **오프사이트 백업**

```bash
# 로그 권한 설정
chmod 600 logs/*.log
chown user:user logs/*.log

# 자동 삭제 (30일 후)
find logs/ -name "*.log" -mtime +30 -delete
```

---

## 🎓 실전 사용 예제

### 예제 1: 일일 보안 점검

```bash
#!/bin/bash
# daily_check.sh - 매일 아침 실행

echo "=== 일일 보안 점검 ==="

# 1. 서비스 상태
./status.sh

# 2. 최근 24시간 통계
curl -s http://localhost:8000/api/stats/overview | jq

# 3. 상위 위협 IP
curl -s http://localhost:8000/api/stats/top-threats?limit=5 | jq

# 4. 탐지율
curl -s http://localhost:8000/api/analysis/detection-metrics?hours=24 | jq

# 5. 차단된 IP
curl -s http://localhost:8000/api/blocked-ips | jq

# Cron: 매일 오전 9시
# 0 9 * * * /path/to/daily_check.sh | mail -s "Daily Security Report" admin@example.com
```

---

### 예제 2: 주간 보고서 자동 생성

```python
# weekly_report.py

import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

# 지난 주 날짜
end = datetime.now()
start = end - timedelta(days=7)

# 보고서 생성
response = requests.post(f"{API_URL}/api/reports/generate", json={
    "start_time": start.isoformat(),
    "end_time": end.isoformat(),
    "report_type": "summary",
    "format": "pdf"
})

if response.json()['success']:
    print(f"✅ 주간 보고서 생성: {response.json()['report_file']}")
else:
    print(f"❌ 실패: {response.json()['error']}")

# Cron: 매주 월요일 오전 10시
# 0 10 * * 1 /path/to/venv/bin/python3 /path/to/weekly_report.py
```

---

### 예제 3: 긴급 알림 설정

```python
# alert_webhook.py - Slack 알림

import requests

def send_slack_alert(threat):
    webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    
    message = {
        "text": f"🚨 긴급: 위협 탐지!",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*IP:* `{threat['ip']}`\n*점수:* {threat['score']}\n*이유:* {threat['reason']}"
                }
            }
        ]
    }
    
    requests.post(webhook_url, json=message)

# agent/security_agent.py에 통합
```

---

## 🔗 추가 리소스

### 공식 문서
- [Suricata 문서](https://suricata.io/docs/)
- [Ollama 문서](https://github.com/ollama/ollama)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Flask 문서](https://flask.palletsprojects.com/)

### 커뮤니티
- GitHub Discussions
- Discord Server (if available)

### 지원
- 🐛 버그 리포트: GitHub Issues
- 💡 기능 제안: GitHub Discussions
- 🔒 보안 취약점: security@your-domain.com

---

**더 궁금한 점이 있나요? GitHub Issues에 질문해주세요! 😊**