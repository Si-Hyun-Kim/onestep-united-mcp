# api/routes/logs.py
"""
로그 관련 API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
sys.path.append('../../mcp_server')
from log_collectors import SuricataCollector, HexStrikeCollector

router = APIRouter()
suricata_collector = SuricataCollector()
hexstrike_collector = HexStrikeCollector()

@router.get("/suricata/recent")
async def get_recent_suricata_logs(
    count: int = Query(50, ge=1, le=500),
    severity: Optional[str] = None
):
    """최근 Suricata 로그"""
    try:
        logs = await suricata_collector.get_recent_logs(count)
        
        if severity and severity != "all":
            logs = [log for log in logs if log.get('severity') == severity]
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hexstrike/recent")
async def get_recent_hexstrike_logs(
    count: int = Query(50, ge=1, le=500)
):
    """최근 HexStrike 로그"""
    try:
        logs = await hexstrike_collector.get_recent_logs(count)
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_logs(
    query: str = Query(..., min_length=1),
    source: str = Query("suricata", regex="^(suricata|hexstrike|all)$")
):
    """로그 검색"""
    try:
        results = []
        
        if source in ["suricata", "all"]:
            suricata_logs = await suricata_collector.get_recent_logs(500)
            for log in suricata_logs:
                if query.lower() in json.dumps(log).lower():
                    results.append({"source": "suricata", "log": log})
        
        if source in ["hexstrike", "all"]:
            hexstrike_logs = await hexstrike_collector.get_recent_logs(500)
            for log in hexstrike_logs:
                if query.lower() in json.dumps(log).lower():
                    results.append({"source": "hexstrike", "log": log})
        
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))