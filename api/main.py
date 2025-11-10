#!/usr/bin/env python3
"""
FastAPI Backend - 실제 데이터 버전
MCP 서버가 저장한 data/alerts.json, data/rules.json 읽기
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import json
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
ALERTS_FILE = "/var/log/suricata/fast.json"
RULES_FILE = "/etc/suricata/rules/suricata.rules"

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

def load_rules() -> list[dict]:
    """생성된 룰 로드"""
    try:
        if RULES_FILE.exists():
            with open(RULES_FILE, "r") as f:
                data = json.load(f)
                return data.get("rules", [])
        return []
    except Exception as e:
        print(f"[API] ❌ 룰 로드 실패: {e}")
        return []

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
        "data_source": "MCP Server (data/alerts.json, data/rules.json)"
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
    """활성 룰 조회 (AI 생성 룰 포함)"""
    rules = load_rules()
    
    # AI 생성 룰 변환
    ai_rules = [
        {
            "sid": 9000000 + i,
            "action": "alert",
            "message": r.get("alert", "AI Generated Rule"),
            "category": "ai-generated",
            "file": r.get("file", "auto_generated.rules"),
            "rule": r.get("rule", ""),
            "timestamp": r.get("timestamp", "")
        }
        for i, r in enumerate(rules)
    ]
    
    # 기본 Suricata 룰 (예시)
    default_rules = [
        {"sid": 2100001, "action": "alert", "message": "ET SCAN Potential SSH Scan", "category": "attempted-recon", "file": "emerging-scan.rules"},
        {"sid": 2100002, "action": "drop", "message": "ET MALWARE Botnet", "category": "trojan", "file": "emerging-malware.rules"},
        {"sid": 2100003, "action": "alert", "message": "ET WEB_SERVER SQL Injection", "category": "web-application-attack", "file": "emerging-web.rules"},
    ]
    
    all_rules = default_rules + ai_rules
    
    if category != 'all':
        all_rules = [r for r in all_rules if r['category'] == category]
    
    return {"rules": all_rules}

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