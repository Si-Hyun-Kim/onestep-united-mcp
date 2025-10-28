# api/routes/analysis.py
"""
분석 관련 API
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import sys
sys.path.append('../../mcp_server')
from log_collectors import SuricataCollector, HexStrikeCollector, LogAnalyzer

router = APIRouter()
suricata_collector = SuricataCollector()
hexstrike_collector = HexStrikeCollector()

@router.get("/compare")
async def compare_logs(time_window: int = 60):
    """Red vs Blue 비교 분석"""
    try:
        cutoff = datetime.now() - timedelta(minutes=time_window)
        
        suricata_logs = await suricata_collector.get_logs_since(cutoff)
        hexstrike_logs = await hexstrike_collector.get_logs_since(cutoff)
        
        # 상관관계 분석
        correlation = LogAnalyzer.correlate_by_ip(suricata_logs, hexstrike_logs)
        
        # 성능 지표
        metrics = LogAnalyzer.calculate_metrics(suricata_logs, hexstrike_logs)
        
        return {
            "success": True,
            "time_window_minutes": time_window,
            "suricata_count": len(suricata_logs),
            "hexstrike_count": len(hexstrike_logs),
            "correlation": correlation,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detection-metrics")
async def get_detection_metrics(hours: int = 24):
    """탐지 성능 지표"""
    try:
        cutoff = datetime.now() - timedelta(hours=hours)
        
        suricata_logs = await suricata_collector.get_logs_since(cutoff)
        hexstrike_logs = await hexstrike_collector.get_logs_since(cutoff)
        
        metrics = LogAnalyzer.calculate_metrics(suricata_logs, hexstrike_logs)
        
        return {
            "success": True,
            "hours": hours,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

