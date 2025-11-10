"""
FastAPI 백엔드 서버
REST API 및 WebSocket 제공
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio
import json
import sys

sys.path.append('../mcp_server')
from log_collectors import SuricataCollector, HexStrikeCollector, LogAnalyzer
from rule_manager import SuricataRuleManager

from routes import logs, rules, reports, analysis
from models import *
from websocket import WebSocketManager

# FastAPI 앱 생성
app = FastAPI(
    title="Security Dashboard API",
    description="AI 기반 자동 보안 시스템 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 컴포넌트 초기화
suricata_collector = SuricataCollector()
hexstrike_collector = HexStrikeCollector()
rule_manager = SuricataRuleManager()
ws_manager = WebSocketManager()

# 라우터 등록
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/")
async def root():
    """API 루트"""
    return {
        "service": "Security Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "suricata_collector": "ok",
            "hexstrike_collector": "ok",
            "rule_manager": "ok"
        }
    }


@app.get("/api/stats/overview")
async def get_overview_stats():
    """전체 통계 개요"""
    try:
        # 최근 24시간 로그
        cutoff = datetime.now() - timedelta(hours=24)
        suricata_logs = await suricata_collector.get_logs_since(cutoff)
        hexstrike_logs = await hexstrike_collector.get_logs_since(cutoff)
        
        # 통계 계산
        total_alerts = len(suricata_logs)
        total_attacks = len(hexstrike_logs)
        
        # 심각도 분포
        severity_dist = {}
        for log in suricata_logs:
            sev = log.get('severity', 'low')
            severity_dist[sev] = severity_dist.get(sev, 0) + 1
        
        # 탐지 지표
        metrics = LogAnalyzer.calculate_metrics(suricata_logs, hexstrike_logs)
        
        # 활성 룰 개수
        active_rules = await rule_manager.get_active_rules()
        
        return {
            "total_alerts_24h": total_alerts,
            "total_attacks_24h": total_attacks,
            "severity_distribution": severity_dist,
            "detection_rate": metrics['detection_rate'],
            "active_rules_count": len(active_rules),
            "last_update": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/timeline")
async def get_timeline_stats(hours: int = 24):
    """시간대별 통계"""
    try:
        cutoff = datetime.now() - timedelta(hours=hours)
        suricata_logs = await suricata_collector.get_logs_since(cutoff)
        
        # 시간대별 집계
        from collections import defaultdict
        hourly_data = defaultdict(int)
        
        for log in suricata_logs:
            try:
                timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                hour_key = timestamp.strftime('%Y-%m-%d %H:00:00')
                hourly_data[hour_key] += 1
            except:
                continue
        
        # 정렬된 시간대별 데이터
        timeline = [
            {"time": time, "count": count}
            for time, count in sorted(hourly_data.items())
        ]
        
        return {
            "hours": hours,
            "timeline": timeline,
            "total_alerts": sum(hourly_data.values())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/top-threats")
async def get_top_threats(limit: int = 10):
    """상위 위협 IP"""
    try:
        suricata_logs = await suricata_collector.get_recent_logs(500)
        
        from collections import defaultdict
        ip_stats = defaultdict(lambda: {"count": 0, "severity_score": 0})
        
        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        
        for log in suricata_logs:
            ip = log.get('src_ip')
            if not ip:
                continue
            
            ip_stats[ip]["count"] += 1
            weight = severity_weights.get(log.get('severity', 'low'), 1)
            ip_stats[ip]["severity_score"] += weight
        
        # 정렬 및 상위 N개
        top_threats = sorted(
            [
                {"ip": ip, **stats}
                for ip, stats in ip_stats.items()
            ],
            key=lambda x: x["severity_score"],
            reverse=True
        )[:limit]
        
        return {
            "threats": top_threats,
            "count": len(top_threats)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """실시간 로그 스트리밍 WebSocket"""
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # 최근 로그 가져오기
            recent_logs = await suricata_collector.get_recent_logs(10)
            
            if recent_logs:
                await ws_manager.send_personal(
                    json.dumps({
                        "type": "logs",
                        "data": recent_logs,
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
            
            # 5초마다 업데이트
            await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/api/action/block-ip")
async def block_ip(request: BlockIPRequest):
    """IP 차단"""
    try:
        import subprocess
        
        # iptables로 차단
        cmd = f"sudo iptables -A INPUT -s {request.ip} -j DROP"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 로그 기록
            from pathlib import Path
            log_file = Path("./logs/actions/blocks.log")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "BLOCK",
                "ip": request.ip,
                "reason": request.reason,
                "user": "admin"  # 실제로는 인증된 사용자
            }
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            return {
                "success": True,
                "message": f"IP {request.ip} blocked successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.stderr)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/action/unblock-ip")
async def unblock_ip(request: UnblockIPRequest):
    """IP 차단 해제"""
    try:
        import subprocess
        
        cmd = f"sudo iptables -D INPUT -s {request.ip} -j DROP"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"IP {request.ip} unblocked successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.stderr)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/blocked-ips")
async def get_blocked_ips():
    """차단된 IP 목록"""
    try:
        import subprocess
        
        cmd = "sudo iptables -L INPUT -n | grep DROP"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        blocked_ips = []
        for line in result.stdout.split('\n'):
            if 'DROP' in line:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[3]
                    if ip != '0.0.0.0/0':
                        blocked_ips.append(ip)
        
        return {
            "blocked_ips": blocked_ips,
            "count": len(blocked_ips)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )