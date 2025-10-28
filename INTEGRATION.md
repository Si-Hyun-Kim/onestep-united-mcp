# 🔗 시스템 통합 가이드

## 📋 목차

1. [초기 설정](#초기-설정)
2. [HexStrike AI 연동](#hexstrike-ai-연동)
3. [Suricata IPS 설정](#suricata-ips-설정)
4. [Ollama 최적화](#ollama-최적화)
5. [프로덕션 배포](#프로덕션-배포)
6. [모니터링 및 로깅](#모니터링-및-로깅)
7. [백업 및 복구](#백업-및-복구)
8. [트러블슈팅](#트러블슈팅)

---

## 초기 설정

### 1. 전체 설치

```bash
# 레포지토리 클론
git clone <your-repo-url>
cd security-automation

# 자동 설치 실행
chmod +x setup.sh
./setup.sh

# 환경 변수 설정
cp .env.example .env
nano .env  # SECRET_KEY 등 수정
```

### 2. 초기 관리자 계정 생성

```python
# dashboard/app.py에서 USERS 딕셔너리 수정
USERS = {
    'admin': {
        'password': 'your-secure-password',  # 변경 필수!
        'mfa_secret': None,
        'role': 'admin'
    }
}
```

### 3. 방화벽 설정

```bash
# UFW 방화벽 설정 (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8080/tcp  # Dashboard
sudo ufw allow 8000/tcp  # API (optional, 내부만 접근 권장)
sudo ufw deny 9000/tcp   # MCP (외부 차단)
sudo ufw enable

# iptables 설정 확인
sudo iptables -L -n
```

---

## HexStrike AI 연동

### Red Team 서버 설정

#### 방법 1: rsync를 통한 로그 동기화 (추천)

```bash
# Red Team 서버에서 실행
# 10초마다 자동 동기화
watch -n 10 rsync -avz --progress \
  /var/log/hexstrike/*.json \
  blue-team-user@blue-team-ip:/path/to/security-automation/logs/hexstrike/
```

#### 방법 2: SSH 마운트

```bash
# Blue Team 서버에서 실행
# Red Team의 로그 디렉토리를 마운트
sshfs red-team-user@red-team-ip:/var/log/hexstrike \
  /path/to/security-automation/logs/hexstrike

# 자동 마운트 (/etc/fstab)
echo "red-team-user@red-team-ip:/var/log/hexstrike /path/to/security-automation/logs/hexstrike fuse.sshfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
```

#### 방법 3: Syslog 전송

```bash
# Red Team 서버 (/etc/rsyslog.conf)
*.* @@blue-team-ip:514

# Blue Team 서버
sudo apt install rsyslog
sudo systemctl start rsyslog
```

### HexStrike 로그 포맷 검증

```bash
# 로그 샘플 확인
cat logs/hexstrike/attack_*.json

# 예상 형식:
{
  "timestamp": "2025-01-17T10:30:15Z",
  "attack_id": "HEX-123456",
  "attack_type": "SQL Injection",
  "source_ip": "192.168.1.100",
  "target": "http://10.0.0.1:3000",
  "payload": "' OR '1'='1",
  "success": true,
  "response_code": 200
}
```

---

## Suricata IPS 설정

### 1. Suricata 설치 및 기본 설정

```bash
# 설치
sudo add-apt-repository ppa:oisf/suricata-stable
sudo apt update
sudo apt install suricata

# 설정 파일 편집
sudo nano /etc/suricata/suricata.yaml
```

### 2. 중요 설정 항목

```yaml
# /etc/suricata/suricata.yaml

# 네트워크 인터페이스
af-packet:
  - interface: eth0  # 모니터링할 인터페이스
    threads: auto
    
# 홈 네트워크
vars:
  address-groups:
    HOME_NET: "[10.0.0.0/8,192.168.0.0/16,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"
    
# 로그 설정
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - alert:
            payload: yes
            payload-buffer-size: 4kb
            payload-printable: yes
            packet: yes
            metadata: yes
            
# 룰 파일
rule-files:
  - /etc/suricata/rules/*.rules
  - /path/to/security-automation/rules/custom/auto_generated.rules
```

### 3. Suricata 시작 및 검증

```bash
# 설정 테스트
sudo suricata -T -c /etc/suricata/suricata.yaml

# 시작
sudo systemctl start suricata
sudo systemctl enable suricata

# 상태 확인
sudo systemctl status suricata

# 로그 확인
sudo tail -f /var/log/suricata/eve.json
```

### 4. 로그 권한 설정

```bash
# 애플리케이션 사용자가 로그를 읽을 수 있도록
sudo usermod -aG suricata $USER
sudo chmod 644 /var/log/suricata/eve.json
```

---

## Ollama 최적화

### 1. Ollama 설정

```bash
# Ollama 서비스 파일 수정
sudo systemctl edit ollama

# 추가:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
Environment="OLLAMA_NUM_PARALLEL=2"  # 동시 요청 수
Environment="OLLAMA_MAX_LOADED_MODELS=1"  # 메모리 절약

# 재시작
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 2. 모델 최적화

```bash
# 더 작은 모델 사용 (메모리 부족 시)
ollama pull qwen2.5:3b

# 또는 양자화 모델
ollama pull qwen2.5:7b-q4_0
```

### 3. GPU 가속 (NVIDIA GPU 사용 시)

```bash
# NVIDIA 드라이버 확인
nvidia-smi

# CUDA 버전 확인
nvcc --version

# Ollama는 자동으로 GPU 사용
# 확인: ollama run 실행 시 GPU 사용량 증가
```

---

## 프로덕션 배포

### 1. systemd 서비스 설치

```bash
# 서비스 자동 설치
sudo ./install_services.sh

# 수동 설치
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-server security-agent security-api security-dashboard
```

### 2. Nginx 리버스 프록시 (HTTPS)

```bash
# Nginx 설치
sudo apt install nginx certbot python3-certbot-nginx

# 설정 파일
sudo nano /etc/nginx/sites-available/security-dashboard
```

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Let's Encrypt 인증
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # HTTP to HTTPS 리다이렉트
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 인증서
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API (선택사항 - 내부만 접근)
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# 설정 활성화
sudo ln -s /etc/nginx/sites-available/security-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Let's Encrypt SSL 인증서
sudo certbot --nginx -d your-domain.com
```

### 3. 보안 강화

```bash
# 1. 비밀번호 강도 증가
# dashboard/app.py에서 bcrypt 사용

# 2. 세션 보안
# dashboard/config.py
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# 3. Rate Limiting (Flask-Limiter)
pip install Flask-Limiter
```

```python
# dashboard/app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    ...
```

### 4. 로그 로테이션

```bash
# /etc/logrotate.d/security-dashboard
/path/to/security-automation/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 user user
    sharedscripts
    postrotate
        systemctl reload security-dashboard > /dev/null 2>&1 || true
    endscript
}
```

---

## 모니터링 및 로깅

### 1. 시스템 모니터링

```bash
# 서비스 상태 확인
./status.sh

# 리소스 사용량 모니터링
htop

# 로그 실시간 확인
# MCP Server
sudo journalctl -u mcp-server -f

# AI Agent
sudo journalctl -u security-agent -f

# API
sudo journalctl -u security-api -f

# Dashboard
sudo journalctl -u security-dashboard -f
```

### 2. Grafana + Prometheus (고급)

```bash
# Prometheus 설치
sudo apt install prometheus

# 설정 (/etc/prometheus/prometheus.yml)
scrape_configs:
  - job_name: 'security-api'
    static_configs:
      - targets: ['localhost:8000']
  
  - job_name: 'security-dashboard'
    static_configs:
      - targets: ['localhost:8080']

# Grafana 설치
sudo apt install grafana

# 시작
sudo systemctl start prometheus grafana-server
```

---

## 백업 및 복구

### 1. 자동 백업 스크립트

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/security-automation"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 설정 파일
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    .env agent/config.yaml dashboard/config.py

# 룰 파일
tar -czf $BACKUP_DIR/rules_$DATE.tar.gz rules/

# 데이터베이스 (if any)
# sqlite3 security.db .dump > $BACKUP_DIR/db_$DATE.sql

# 최근 7일만 유지
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
```

```bash
# Cron 설정 (매일 새벽 3시)
crontab -e

# 추가:
0 3 * * * /path/to/security-automation/backup.sh
```

### 2. 복구

```bash
# 설정 복구
tar -xzf backup/config_20250117_030000.tar.gz

# 룰 복구
tar -xzf backup/rules_20250117_030000.tar.gz

# 서비스 재시작
./restart_all.sh
```

---

## 트러블슈팅

### 문제 1: Ollama 연결 실패

**증상:** `❌ Ollama 서버에 연결할 수 없습니다!`

**해결:**
```bash
# Ollama 상태 확인
pgrep -x ollama || echo "Not running"

# Ollama 시작
ollama serve

# 백그라운드 실행
nohup ollama serve > logs/ollama.log 2>&1 &

# 포트 확인
netstat -tlnp | grep 11434
```

### 문제 2: Suricata 로그 읽기 실패

**증상:** `⚠️  Suricata log not found`

**해결:**
```bash
# 로그 파일 확인
ls -la /var/log/suricata/eve.json

# 권한 확인
sudo chmod 644 /var/log/suricata/eve.json

# Suricata 재시작
sudo systemctl restart suricata
```

### 문제 3: MFA QR 코드 스캔 안 됨

**증상:** Google Authenticator에서 QR 코드 인식 실패

**해결:**
```python
# dashboard/app.py에서 시크릿 확인
print(f"MFA Secret: {secret}")

# 수동 입력: Google Authenticator → 수동 입력
```

### 문제 4: 메모리 부족

**증상:** Ollama가 응답하지 않음

**해결:**
```bash
# 더 작은 모델 사용
ollama pull qwen2.5:3b

# agent/config.yaml 수정
ollama:
  model: "qwen2.5:3b"

# 에이전트 재시작
sudo systemctl restart security-agent
```

### 문제 5: iptables 권한 오류

**증상:** `sudo: no tty present and no askpass program specified`

**해결:**
```bash
# sudoers 파일 수정
sudo visudo

# 추가 (your-user를 실제 사용자명으로):
your-user ALL=(ALL) NOPASSWD: /usr/sbin/iptables
```

### 문제 6: Port already in use

**증상:** `Address already in use: 8080`

**해결:**
```bash
# 포트 사용 프로세스 확인
sudo lsof -i :8080

# 프로세스 종료
kill -9 <PID>

# 또는 전체 정지
./stop_all.sh
```

### 문제 7: HexStrike 로그 없음

**증상:** `⚠️  HexStrike logs not found`

**해결:**
```bash
# 로그 디렉토리 확인
ls -la logs/hexstrike/

# Red Team에서 로그 전송 확인
# rsync 상태 확인

# 샘플 로그 생성 (테스트용)
echo '{"timestamp":"2025-01-17T10:00:00Z","attack_type":"test","source_ip":"1.2.3.4","success":false}' > logs/hexstrike/test.json
```

---

## 📞 지원

문제가 해결되지 않으면:

1. 로그 확인: `tail -f logs/*.log`
2. 시스템 테스트: `./test_system.sh`
3. GitHub Issues 등록
4. 로그 파일 첨부

---

**다음 단계:** [프로덕션 배포 체크리스트](DEPLOYMENT.md)