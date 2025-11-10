#!/usr/bin/env python3

"""
api/main.py
FastAPI Backend - 실제 데이터 버전
MCP 서버가 저장한 data/alerts.json, data/rules.json 읽기
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import json
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter

import uvicorn  # (if __name__ == "__main__" 에서 사용할 것이므로)
import asyncio  # 실시간 감시(tail)를 위해
from typing import List, Set # Set을 추가

app = FastAPI(
    title="Suricata Monitoring API",
    description="실시간 Suricata 로그 API",
    version="3.0.0"
)

# --- WebSocket 연결 관리 ---
# 현재 연결된 모든 클라이언트(대시보드)를 저장할 집합(Set)
connected_clients: Set[WebSocket] = set()

# 파일의 마지막으로 읽은 위치를 저장 (서버가 켜져 있는 동안)
last_file_position = 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 파일 경로
ALERTS_FILE = Path("/var/log/suricata/eve.json")
RULES_FILE = Path("/etc/suricata/rules/suricata.rules")

# ================== 데이터 로드 함수 ==================

def load_alerts() -> list[dict]:
    """알림 데이터 로드 (JSONL 형식 .json 파일 파서로 변경 및 데이터 평탄화)"""
    alerts_list = []
    try:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # 각 줄을 개별 JSON으로 파싱
                        event_data = json.loads(line)
                        
                        # 'alert' 타입만 필터링
                        if event_data.get("event_type") == "alert":
                            
                            alert_details = event_data.get('alert')
                            if not alert_details:
                                continue # alert 객체가 없는 경우 건너뛰기

                            # (중요) 데이터를 평탄화(Flatten)하여 API의 다른 부분이 사용하기 쉽게 만듦
                            alerts_list.append({
                                "timestamp": event_data.get("timestamp"),
                                "src_ip": event_data.get("src_ip"),
                                "dest_ip": event_data.get("dest_ip"),
                                "src_port": event_data.get("src_port"),
                                "dest_port": event_data.get("dest_port"),
                                "proto": event_data.get("proto"),
                                
                                # 'alert' 하위 객체에서 정보 추출
                                "signature": alert_details.get("signature"),
                                "severity": alert_details.get("severity"), # 1, 2, 3 등
                                "category": alert_details.get("category"),
                                
                                # (선택) 원본 룰 SID
                                "gid": alert_details.get("gid"),
                                "sid": alert_details.get("signature_id") 
                            })

                    except json.JSONDecodeError as json_err:
                        # 파일의 특정 줄 파싱 실패 (무시하고 계속)
                        print(f"[API] ⚠️ 알림 JSONL 파싱 에러: {json_err} | 라인: {line[:100]}...")
        else:
             print(f"[API] ❌ 알림 파일 없음: {ALERTS_FILE}")
             
    except Exception as e:
        print(f"[API] ❌ 알림 파일 읽기 실패: {e}")
    
    # data.get("alerts", []) 대신 파싱한 리스트를 직접 반환
    return alerts_list

def parse_rule_metadata(metadata_str: str) -> dict:
    """룰의 ( ) 안에 있는 메타데이터를 파싱하는 헬퍼 함수"""
    meta_dict = {}
    try:
        # (msg:"..."; sid:123; rev:1; ... )
        # 정규표현식을 사용해 key:"value"; 또는 key:value; 형태를 찾음
        pairs = re.findall(r'([\w\.-]+):(?:\"(.*?)\"|([^;]+));', metadata_str)
        for pair in pairs:
            key = pair[0]
            # 따옴표가 있는 값(pair[1])이 우선, 없으면 따옴표 없는 값(pair[2])
            value = pair[1] if pair[1] else pair[2].strip()
            meta_dict[key] = value
    except Exception as e:
        print(f"[API] ⚠️ 메타데이터 파싱 에러: {e} | on: {metadata_str[:50]}...")
    return meta_dict

def load_rules() -> list[dict]:
    """생성된 룰 로드 (JSON이 아닌 .rules 텍스트 파일 파서로 변경)"""
    rules_list = []
    try:
        if RULES_FILE.exists():
            with open(RULES_FILE, "r") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    # 주석(#)이나 빈 줄 건너뛰기
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        # 룰을 공백 기준으로 분리 (첫 7개 요소가 중요)
                        parts = line.split(maxsplit=6)
                        if len(parts) < 7:
                            print(f"[API] ⚠️ 룰 형식 오류 (7부분 미만): {line[:50]}...")
                            continue 

                        action = parts[0]
                        metadata_str = parts[6] # (msg... 부터 끝까지
                        
                        # 메타데이터 파싱
                        metadata = parse_rule_metadata(metadata_str)
                        
                        rules_list.append({
                            "sid": metadata.get("sid", f"no-sid-{i}"),
                            "action": action.lower(), # 'alert', 'drop' 등
                            "message": metadata.get("msg", "N/A"),
                            "category": metadata.get("classtype", "N/A"),
                            "file": "suricata.rules", # 파일명
                            "rule": line, # 전체 룰 텍스트
                            # (선택) 타임스탬프 정보가 있다면 추가
                            "timestamp": metadata.get("updated_at", metadata.get("created_at", "")) 
                        })
                    except Exception as e:
                        print(f"[API] ⚠️ 룰 파싱 중 에러: {e} | 라인: {line[:50]}...")
        else:
            print(f"[API] ❌ 룰 파일 없음: {RULES_FILE}")
            
    except Exception as e:
        print(f"[API] ❌ 룰 파일 읽기 실패: {e}")
    
    return rules_list

# ================== API 엔드포인트 ==================

@app.get("/")
async def root():
    alerts = load_alerts()
    rules = load_rules()
    
    return {
        "service": "Suricata Monitoring API",
        "version": "3.0.0",
        "status": "running",
        "alerts_loaded": len(alerts),
        "rules_generated": len(rules),
        "data_source": "MCP Server (/var/log/suricata/eve.json, /etc/suricata/rules/suricata.rules)"
    }

@app.get("/api/stats/overview")
async def get_stats_overview():
    """전체 통계"""
    alerts = load_alerts()
    
    if not alerts:
        return {
            "total_alerts_24h": 0,
            "total_attacks_24h": 0,
            "detection_rate": 100,
            "active_rules_count": 0,
            "severity_distribution": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
    
    # (수정) 현재 시간을 UTC(시간대 정보 포함) 기준으로 변경
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_alerts = []
    
    for a in alerts:
        try:
            # (수정) .replace() 제거, fromisoformat이 +0900을 알아서 처리
            alert_time = datetime.fromisoformat(a['timestamp'])
            if alert_time > cutoff:
                recent_alerts.append(a)
        except (ValueError, TypeError):
            # 타임스탬프 형식이 잘못된 경우 무시
            continue
            
    by_severity = Counter(a['severity'] for a in recent_alerts)
    
    return {
        "total_alerts_24h": len(recent_alerts),
        "total_attacks_24h": len(recent_alerts),
        "critical_alerts_24h": by_severity.get(1, 0),
        "detection_rate": 100,
        "active_rules_count": len(load_rules()),
        "severity_distribution": {
            "critical": by_severity.get(1, 0),
            "high": by_severity.get(2, 0),
            "medium": by_severity.get(3, 0),
            "low": by_severity.get(4, 0) + by_severity.get(5, 0) # (예시: 4 이상은 low)
        }
    }

@app.get("/api/stats/timeline")
async def get_stats_timeline(hours: int = 24):
    """시간대별 타임라인"""
    alerts = load_alerts()
    
    # (수정) 현재 시간을 UTC(시간대 정보 포함) 기준으로 변경
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_alerts = []

    for a in alerts:
        try:
            # (수정) .replace() 제거
            alert_time = datetime.fromisoformat(a['timestamp'])
            if alert_time > cutoff:
                recent_alerts.append(a)
        except (ValueError, TypeError):
            continue

    timeline = {}
    for alert in recent_alerts:
        # (수정) .replace() 제거
        hour = datetime.fromisoformat(alert['timestamp']).strftime('%H:00')
        timeline[hour] = timeline.get(hour, 0) + 1
    
    timeline_list = [{"time": k, "count": v} for k, v in sorted(timeline.items())]
    
    return {"timeline": timeline_list}

@app.get("/api/logs/suricata")
async def get_suricata_logs(count: int = 50, severity: Optional[str] = None):
    """Suricata 로그 조회"""
    alerts = load_alerts()
    
    # 최신순 정렬
    alerts_sorted = sorted(alerts, key=lambda x: x['timestamp'], reverse=True)
    logs = alerts_sorted[:count]
    
    if severity and severity != 'all':
        severity_map = {'critical': 1, 'high': 2, 'medium': 3, 'low': 3}
        sev_num = severity_map.get(severity.lower())
        if sev_num:
            logs = [log for log in logs if log['severity'] == sev_num]
    
    return {"count": len(logs), "logs": logs}

@app.get("/api/logs/search")
async def search_logs(query: str):
    """로그 검색"""
    alerts = load_alerts()
    query_lower = query.lower()
    results = []
    
    for alert in alerts:
        if (query_lower in alert['src_ip'].lower() or
            query_lower in alert['dest_ip'].lower() or
            query_lower in alert['signature'].lower() or
            query_lower in alert.get('category', '').lower()):
            results.append(alert)
    
    # 최신순 정렬
    results_sorted = sorted(results, key=lambda x: x['timestamp'], reverse=True)
    
    return {"query": query, "count": len(results_sorted), "results": results_sorted[:50]}

@app.get("/api/rules/active")
async def get_active_rules(category: str = "all"):
    """활성 룰 조회 (실제 파싱된 룰 사용)"""
    
    all_rules = load_rules() # <--- 실제 파싱된 룰을 가져옴

    if category != 'all' and category:
        # category가 N/A인 경우를 대비해 .get() 사용
        all_rules = [r for r in all_rules if r.get('category') == category]
    
    # 프론트엔드가 total 값을 사용할 수 있도록 total도 함께 반환
    return {"rules": all_rules, "total": len(all_rules)}

@app.get("/api/rules/search")
async def search_rules(query: str):
    """룰 검색 (새 기능!)"""
    rules = load_rules()
    query_lower = query.lower()
    results = []
    
    for i, r in enumerate(rules):
        rule_text = r.get("rule", "").lower()
        alert_text = r.get("alert", "").lower()
        
        if query_lower in rule_text or query_lower in alert_text:
            results.append({
                "sid": 9000000 + i,
                "action": "alert",
                "message": r.get("alert", "AI Generated Rule"),
                "category": "ai-generated",
                "file": r.get("file", "auto_generated.rules"),
                "rule": r.get("rule", ""),
                "timestamp": r.get("timestamp", ""),
                "severity": r.get("severity", 3)
            })
    
    return {"query": query, "count": len(results), "results": results}

@app.get("/api/health")
async def health_check():
    alerts = load_alerts()
    rules = load_rules()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "alerts_count": len(alerts),
        "rules_count": len(rules),
        "data_files": {
            "alerts": str(ALERTS_FILE.exists()),
            "rules": str(RULES_FILE.exists())
        }
    }

# --- 1. WebSocket 연결을 처리하는 엔드포인트 ---
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """
    대시보드(클라이언트)가 이 엔드포인트로 WebSocket 연결을 시도합니다.
    """
    await websocket.accept()
    connected_clients.add(websocket) # 새 클라이언트를 집합에 추가
    print(f"[API]  WebSocket 클라이언트 연결됨. (총 {len(connected_clients)} 명)")
    try:
        while True:
            # 클라이언트로부터 메시지를 받을 수도 있지만, 지금은 받기만 대기
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 클라이언트 연결이 끊어지면 집합에서 제거
        connected_clients.remove(websocket)
        print(f"[API] WebSocket 클라이언트 연결 끊어짐. (남은 {len(connected_clients)} 명)")

# --- 2. eve.json 파일을 실시간 감시(tail)하는 함수 ---
async def tail_eve_json_file():
    """
    FastAPI 서버 시작 시 백그라운드에서 실행될 함수.
    eve.json 파일의 변경 사항을 감지하여 새 알림을 WebSocket으로 PUSH합니다.
    """
    global last_file_position
    print("[API] 🚀 실시간 알림 감시 시작 (tail_eve_json_file)")

    # 시작 시 파일의 현재 끝 위치 저장
    try:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, "r") as f:
                f.seek(0, 2) # 파일의 맨 끝으로 이동
                last_file_position = f.tell() # 현재 위치(파일 크기) 저장
    except Exception as e:
        print(f"[API] ❌ 초기 파일 위치 읽기 실패: {e}")

    while True:
        try:
            if ALERTS_FILE.exists():
                with open(ALERTS_FILE, "r") as f:
                    # 마지막으로 읽은 위치로 이동
                    f.seek(last_file_position)
                    new_lines = f.readlines()
                    
                    # 파일의 현재 끝 위치를 다음 루프를 위해 갱신
                    last_file_position = f.tell()

                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event_data = json.loads(line)
                        
                        # (중요) 'alert' 타입만 필터링
                        if event_data.get("event_type") == "alert":
                            
                            alert_details = event_data.get('alert')
                            if not alert_details:
                                continue

                            # load_alerts에서 평탄화했던 데이터와 동일한 구조로 만듦
                            alert_payload = {
                                "timestamp": event_data.get("timestamp"),
                                "src_ip": event_data.get("src_ip"),
                                "dest_ip": event_data.get("dest_ip"),
                                "src_port": event_data.get("src_port"),
                                "dest_port": event_data.get("dest_port"),
                                "proto": event_data.get("proto"),
                                "signature": alert_details.get("signature"),
                                "severity": alert_details.get("severity"),
                                "category": alert_details.get("category"),
                                "sid": alert_details.get("signature_id") 
                            }
                            
                            # (중요) 연결된 모든 클라이언트에게 새 알림 PUSH
                            # 여러 클라이언트가 동시에 연결되어 있을 수 있으므로 리스트 복사 후 전송
                            clients_to_send = list(connected_clients) 
                            for client in clients_to_send:
                                try:
                                    # JSON 문자열로 변환하여 전송
                                    await client.send_text(json.dumps(alert_payload))
                                except Exception:
                                    # 전송 실패 시 (연결 끊김 등) 집합에서 제거
                                    connected_clients.remove(client)
                                    
                    except json.JSONDecodeError:
                        continue # 파싱 실패한 줄은 무시
                        
        except Exception as e:
            print(f"[API] ❌ 파일 감시(tail) 중 에러: {e}")
        
        # 1초마다 파일의 변경 사항을 다시 체크
        await asyncio.sleep(1)

# --- 3. FastAPI 시작 시 tail 함수를 백그라운드 작업으로 등록 ---
@app.on_event("startup")
async def on_startup():
    """
    FastAPI 서버가 시작될 때 `tail_eve_json_file` 함수를 
    백그라운드 태스크로 자동 실행합니다.
    """
    asyncio.create_task(tail_eve_json_file())


if __name__ == "__main__":
    import uvicorn
    print("🚀 FastAPI Backend (실제 데이터)")
    print(f"📁 Alerts: {ALERTS_FILE}")
    print(f"📁 Rules: {RULES_FILE}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")