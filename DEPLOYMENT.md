# 🚀 프로덕션 배포 체크리스트

## 📋 배포 전 체크리스트

### 1. 보안 설정 ✅

- [ ] **SECRET_KEY 변경**
  ```bash
  # .env 파일
  SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  ```

- [ ] **기본 비밀번호 변경**
  ```python
  # dashboard/app.py
  USERS = {
      'admin': {
          'password': 'STRONG_PASSWORD_HERE',  # bcrypt 해시 사용 권장
          'mfa_secret': None,
          'role': 'admin'
      }
  }
  ```

- [ ] **MFA 필수 활성화**
  ```bash
  # .env
  MFA_ENABLED=True
  ```

- [ ] **HTTPS 설정 (Nginx + Let's Encrypt)**
  ```bash
  sudo certbot --nginx -d your-domain.com
  ```

- [ ] **방화벽 설정**
  ```bash
  # 필요한 포트만 열기
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP (리다이렉트용)
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw deny 8000/tcp   # API 직접 접근 차단
  sudo ufw deny 9000/tcp   # MCP 차단
  sudo ufw enable
  ```

- [ ] **화이트리스트 설정**
  ```yaml
  # agent/config.yaml
  auto_response:
    whitelist:
      - "YOUR_ADMIN_IP"
      - "YOUR_OFFICE_IP_RANGE"
  ```

### 2. 시스템 설정 ✅

- [ ] **systemd 서비스 등록**
  ```bash
  sudo ./install_services.sh
  sudo systemctl enable mcp-server security-agent security-api security-dashboard
  ```

- [ ] **자동 시작 확인**
  ```bash
  sudo systemctl is-enabled mcp-server
  ```

- [ ] **로그 로테이션 설정**
  ```bash
  sudo nano /etc/logrotate.d/security-dashboard
  ```

- [ ] **백업 스크립트 Cron 등록**
  ```bash
  crontab -e
  # 매일 새벽 3시 백업
  0 3 * * * /path/to/security-automation/backup.sh
  ```

### 3. 성능 최적화 ✅

- [ ] **Ollama 최적화**
  ```bash
  # GPU 사용 확인 (있는 경우)
  nvidia-smi
  
  # 모델 최적화 (메모리 부족 시)
  ollama pull qwen2.5:3b
  ```

- [ ] **데이터베이스 인덱싱** (향후 SQLite/PostgreSQL 사용 시)

- [ ] **Nginx 캐싱 설정**
  ```nginx
  location /static/ {
      expires 1y;
      add_header Cache-Control "public, immutable";
  }
  ```

- [ ] **프로세스 수 조정**
  ```python
  # api/main.py (uvicorn)
  uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
  ```

### 4. 모니터링 설정 ✅

- [ ] **서비스 상태 모니터링**
  ```bash
  # 상태 확인 스크립트를 Cron에 추가
  */5 * * * * /path/to/status.sh | mail -s "Security System Status" admin@example.com
  ```

- [ ] **디스크 사용량 모니터링**
  ```bash
  # 로그 디렉토리 크기 확인
  du -sh logs/
  
  # 90% 넘으면 알림
  df -h | awk '$5 > 90 {print $0}'
  ```

- [ ] **메모리 사용량 체크**
  ```bash
  free -h
  ```

### 5. 테스트 ✅

- [ ] **통합 테스트 실행**
  ```bash
  ./test_system.sh
  ```

- [ ] **로그인 테스트**
  - 기본 로그인
  - MFA 인증
  - 잘못된 자격증명 처리

- [ ] **API 엔드포인트 테스트**
  ```bash
  # 헬스 체크
  curl https://your-domain.com/api/health
  
  # 로그 조회
  curl https://your-domain.com/api/logs/suricata/recent
  ```

- [ ] **공격 시뮬레이션 테스트**
  ```bash
  # 취약한 서버에 테스트 공격
  curl "http://localhost:5000/api/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin'\'' OR '\''1'\''='\''1","password":"test"}'
  
  # Suricata 로그 확인
  tail -f /var/log/suricata/eve.json
  
  # 대시보드에서 알림 확인
  ```

### 6. 문서화 ✅

- [ ] **시스템 문서 작성**
  - 아키텍처 다이어그램
  - API 문서
  - 운영 매뉴얼
  - 장애 대응 절차

- [ ] **연락처 정보 업데이트**
  - 관리자 이메일
  - 긴급 연락처
  - 에스컬레이션 절차

---

## 🎯 배포 단계별 가이드

### Phase 1: 개발 환경 (로컬)

```bash
# 1. 설치
./setup.sh

# 2. 테스트
./test_system.sh

# 3. 수동 실행
./start_all.sh

# 4. 기능 테스트
# - 대시보드 접속
# - 로그 확인
# - 룰 추가
# - 공격 시뮬레이션
```

### Phase 2: 스테이징 환경

```bash
# 1. 서버 준비
# - Ubuntu 20.04+ LTS
# - 최소 4GB RAM
# - 10GB 디스크

# 2. 배포
git clone <repo>
cd security-automation
./setup.sh

# 3. 환경 설정
cp .env.example .env
nano .env  # 수정

# 4. systemd 서비스 등록
sudo ./install_services.sh

# 5. 시작
sudo systemctl start mcp-server security-agent security-api security-dashboard

# 6. 테스트
./test_system.sh
```

### Phase 3: 프로덕션 환경

```bash
# 1. 보안 강화
# - 방화벽 설정
# - HTTPS 설정
# - MFA 활성화
# - 강력한 비밀번호

# 2. Nginx 리버스 프록시
sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 3. 모니터링 설정
# - 로그 모니터링
# - 성능 모니터링
# - 알림 설정

# 4. 백업 설정
# - 자동 백업 스크립트
# - 오프사이트 백업

# 5. 최종 테스트
# - 부하 테스트
# - 보안 스캔
# - 침투 테스트
```

---

## 📊 성능 벤치마크

### 권장 사양

| 구분 | 최소 | 권장 | 고성능 |
|------|------|------|--------|
| **CPU** | 2 Core | 4 Core | 8+ Core |
| **RAM** | 4GB | 8GB | 16GB+ |
| **디스크** | 20GB | 50GB | 100GB+ SSD |
| **네트워크** | 100Mbps | 1Gbps | 10Gbps |

### 예상 성능

- **로그 처리**: ~1000 로그/초
- **AI 분석**: ~10 분석/분
- **룰 생성**: ~5 룰/분
- **동시 사용자**: ~50명
- **응답 시간**: < 200ms (평균)

### 성능 최적화 팁

1. **Ollama 모델 선택**
   ```bash
   # 빠른 응답 (낮은 정확도)
   ollama pull qwen2.5:3b
   
   # 균형
   ollama pull qwen2.5:7b  # 권장
   
   # 높은 정확도 (느림)
   ollama pull qwen2.5:14b
   ```

2. **캐싱 활용**
   ```python
   # API에 Redis 캐시 추가
   from redis import Redis
   cache = Redis(host='localhost', port=6379)
   ```

3. **로드 밸런싱** (대규모)
   ```nginx
   upstream security_api {
       server 127.0.0.1:8000;
       server 127.0.0.1:8001;
       server 127.0.0.1:8002;
   }
   ```

---

## 🔍 배포 후 점검

### Day 1 체크리스트

- [ ] 모든 서비스 정상 작동 확인
- [ ] 로그 수집 정상 확인
- [ ] AI 에이전트 분석 정상 확인
- [ ] 대시보드 접속 확인
- [ ] MFA 인증 테스트
- [ ] 백업 실행 확인

### Week 1 체크리스트

- [ ] 성능 메트릭 수집
- [ ] 오류 로그 검토
- [ ] 탐지율 분석
- [ ] False Positive 조정
- [ ] 사용자 피드백 수집

### Month 1 체크리스트

- [ ] 보안 감사
- [ ] 성능 리뷰
- [ ] 룰 최적화
- [ ] 문서 업데이트
- [ ] 팀 교육

---

## 🆘 긴급 상황 대응

### 시스템 다운

```bash
# 1. 서비스 상태 확인
./status.sh

# 2. 로그 확인
sudo journalctl -u mcp-server -n 100
sudo journalctl -u security-agent -n 100

# 3. 재시작
./restart_all.sh

# 4. 여전히 문제 있으면
./stop_all.sh
# 로그 검토 후
./start_all.sh
```

### 메모리 부족

```bash
# 임시 조치: 에이전트 정지
sudo systemctl stop security-agent

# Ollama 모델 변경
ollama pull qwen2.5:3b

# agent/config.yaml 수정
nano agent/config.yaml
# model: "qwen2.5:3b"

# 재시작
sudo systemctl start security-agent
```

### 디스크 가득 참

```bash
# 오래된 로그 삭제
find logs/ -name "*.log" -mtime +7 -delete

# 오래된 보고서 삭제
find reports/ -name "*.pdf" -mtime +30 -delete

# 로그 로테이션 강제 실행
sudo logrotate -f /etc/logrotate.d/security-dashboard
```

---

## 📞 지원 및 문의

- **문제 발생 시**: GitHub Issues
- **보안 취약점**: security@your-domain.com
- **기술 지원**: support@your-domain.com

---

**배포 성공을 기원합니다! 🎉**