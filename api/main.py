#!/usr/bin/env python3
"""
FastAPI Backend - Suricata 로그 API (확장 버전)
Flask 대시보드와 완전 호환되도록 모든 엔드포인트 제공
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import subprocess
import random

app = FastAPI(
    title="Suricata Monitoring API",
    description="Suricata 보안 로그 API - Flask 대시보드용 확장 버전",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 임시 데이터 저장소
DUMMY_ALERTS = []
BLOCKED_IPS = set()

# 더미 알림 생성 (시작 시)
def generate_dummy_alerts(count=100):
    """테스트용 더미 알림 생성"""
    signatures = [
        "ET SCAN Potential SSH Scan",
        "ET MALWARE Possible Botnet Command",
        "ET WEB_SERVER SQL Injection Attempt",
        "ET POLICY HTTP Client Body Contains Pass =",
        "ET EXPLOIT Possible CVE-2021-44228 Log4j RCE",
    ]
    
    categories = [
        "Attempted Information Leak",
        "A Network Trojan was detected",
        "Web Application Attack",
        "Potential Corporate Privacy Violation",
    ]
    
    ips = [
        "192.168.1.100", "10.0.0.5", "172.16.0.20",
        "203.0.113.45", "198.51.100.23", "192.0.2.150"
    ]
    
    for i in range(count):
        alert = {
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
            "src_ip": random.choice(ips),
            "dest_ip": "8.8.8.8",
            "src_port": random.randint(1024, 65535),
            "dest_port": random.choice([22, 80, 443, 3306, 8080]),
            "severity": random.choice([1, 1, 2, 2, 2, 3, 3, 3, 3, 3]),
            "signature": random.choice(signatures),
            "category": random.choice(categories),
            "proto": random.choice(["TCP", "UDP", "ICMP"])
        }
        DUMMY_ALERTS.append(alert)
    
    DUMMY_ALERTS.sort(key=lambda x: x['timestamp'], reverse=True)

# 앱 시작 시 더미 데이터 생성
generate_dummy_alerts(100)

@app.get("/")
async def root():
    return {
        "service": "Suricata Monitoring API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/api/stats/overview")
async def get_stats_overview():
    """전체 통계 요약"""
    cutoff = datetime.now() - timedelta(hours=24)
    recent_alerts = [a for a in DUMMY_ALERTS if datetime.fromisoformat(a['timestamp']) > cutoff]
    
    by_severity = Counter(a['severity'] for a in recent_alerts)
    by_category = Counter(a['category'] for a in DUMMY_ALERTS[:50])
    top_sources = Counter(a['src_ip'] for a in recent_alerts)
    
    return {
        "total_alerts_24h": len(recent_alerts),
        "total_attacks_24h": len(recent_alerts),
        "detection_rate": 100,
        "active_rules_count": 1523,
        "severity_distribution": {
            "critical": by_severity.get(1, 0),
            "high": by_severity.get(2, 0),
            "medium": by_severity.get(3, 0),
            "low": 0
        },
        "by_severity": dict(by_severity),
        "by_category": dict(by_category),
        "top_sources": dict(top_sources.most_common(10)),
        "blocked_ips": len(BLOCKED_IPS)
    }

@app.get("/api/stats/timeline")
async def get_stats_timeline(hours: int = 24):
    """시간대별 알림 타임라인"""
    cutoff = datetime.now() - timedelta(hours=hours)
    recent_alerts = [a for a in DUMMY_ALERTS if datetime.fromisoformat(a['timestamp']) > cutoff]
    
    timeline = {}
    for alert in recent_alerts:
        hour = datetime.fromisoformat(alert['timestamp']).strftime('%H:00')
        timeline[hour] = timeline.get(hour, 0) + 1
    
    timeline_list = [{"time": k, "count": v} for k, v in sorted(timeline.items())]
    
    return {"timeline": timeline_list}

@app.get("/api/stats/top-threats")
async def get_top_threats(limit: int = 10):
    """상위 위협 IP"""
    ip_counts = Counter(a['src_ip'] for a in DUMMY_ALERTS)
    
    threats = []
    for ip, count in ip_counts.most_common(limit):
        ip_alerts = [a for a in DUMMY_ALERTS if a['src_ip'] == ip]
        severity_score = sum(10 if a['severity'] == 1 else 5 if a['severity'] == 2 else 2 for a in ip_alerts)
        
        threats.append({
            "ip": ip,
            "count": count,
            "severity_score": severity_score
        })
    
    return {"threats": threats}

@app.get("/api/logs/suricata")
async def get_suricata_logs(count: int = 50, severity: Optional[str] = None):
    """Suricata 로그 조회"""
    logs = DUMMY_ALERTS[:count]
    
    if severity and severity != 'all':
        severity_map = {'critical': 1, 'high': 2, 'medium': 3, 'low': 3}
        sev_num = severity_map.get(severity.lower())
        if sev_num:
            logs = [log for log in logs if log['severity'] == sev_num]
    
    return {"count": len(logs), "logs": logs}

@app.get("/api/logs/search")
async def search_logs(query: str):
    """로그 검색"""
    query_lower = query.lower()
    results = []
    
    for alert in DUMMY_ALERTS:
        if (query_lower in alert['src_ip'].lower() or
            query_lower in alert['dest_ip'].lower() or
            query_lower in alert['signature'].lower() or
            query_lower in alert['category'].lower()):
            results.append(alert)
    
    return {"query": query, "count": len(results), "results": results[:50]}

@app.get("/api/rules/active")
async def get_active_rules(category: str = "all"):
    """활성 룰 조회"""
    dummy_rules = [
        {"sid": 2100001, "action": "alert", "message": "ET SCAN Potential SSH Scan", "category": "attempted-recon", "file": "emerging-scan.rules"},
        {"sid": 2100002, "action": "drop", "message": "ET MALWARE Botnet Command", "category": "trojan", "file": "emerging-malware.rules"},
        {"sid": 2100003, "action": "alert", "message": "ET WEB_SERVER SQL Injection", "category": "web-application-attack", "file": "emerging-web.rules"},
        {"sid": 9000001, "action": "alert", "message": "AI Generated - Suspicious Pattern", "category": "attempted-admin", "file": "auto_generated.rules"}
    ]
    
    if category != 'all':
        dummy_rules = [r for r in dummy_rules if r['category'] == category]
    
    return {"rules": dummy_rules}

@app.post("/api/action/block-ip")
async def block_ip(data: Dict):
    """IP 차단"""
    ip = data.get('ip')
    reason = data.get('reason', 'Blocked from API')
    
    if not ip:
        return {"success": False, "error": "IP address required"}
    
    try:
        is_ipv6 = ':' in ip
        cmd = ['sudo', 'ip6tables' if is_ipv6 else 'iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP']
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            BLOCKED_IPS.add(ip)
            return {"success": True, "message": f"IP {ip} blocked successfully", "reason": reason}
        else:
            return {"success": False, "error": f"iptables failed: {result.stderr}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/reports/list")
async def list_reports():
    """생성된 보고서 목록"""
    reports_dir = Path("./reports")
    reports = []
    
    if reports_dir.exists():
        for file in reports_dir.glob("*.pdf"):
            reports.append({
                "filename": file.name,
                "size": file.stat().st_size,
                "created": datetime.fromtimestamp(file.stat().st_ctime).isoformat()
            })
    
    return {"reports": reports}

@app.post("/api/reports/generate")
async def generate_report(data: Dict):
    """보고서 생성"""
    return {
        "success": True,
        "message": "보고서 생성 대기 중",
        "filename": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "alerts_count": len(DUMMY_ALERTS),
        "blocked_ips_count": len(BLOCKED_IPS)
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 FastAPI Backend Starting...")
    print("📊 Generated 100 dummy alerts for testing")
    print("🌐 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
