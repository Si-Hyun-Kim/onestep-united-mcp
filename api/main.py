#!/usr/bin/env python3

"""
api/main.py
FastAPI Backend - 실제 데이터 버전
MCP 서버가 저장한 data/alerts.json, data/rules.json 읽기
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

app = FastAPI(
    title="Suricata Monitoring API",
    description="실시간 Suricata 로그 API",
    version="3.0.0"
)

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
    """알림 데이터 로드"""
    try:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, "r") as f:
                data = json.load(f)
                return data.get("alerts", [])
        return []
    except Exception as e:
        print(f"[API] ❌ 알림 로드 실패: {e}")
        return []

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
    
    cutoff = datetime.now() - timedelta(hours=24)
    recent_alerts = [
        a for a in alerts 
        if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > cutoff
    ]
    
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
            "low": 0
        }
    }

@app.get("/api/stats/timeline")
async def get_stats_timeline(hours: int = 24):
    """시간대별 타임라인"""
    alerts = load_alerts()
    
    cutoff = datetime.now() - timedelta(hours=hours)
    recent_alerts = [
        a for a in alerts 
        if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > cutoff
    ]
    
    timeline = {}
    for alert in recent_alerts:
        hour = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')).strftime('%H:00')
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

if __name__ == "__main__":
    import uvicorn
    print("🚀 FastAPI Backend (실제 데이터)")
    print(f"📁 Alerts: {ALERTS_FILE}")
    print(f"📁 Rules: {RULES_FILE}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")