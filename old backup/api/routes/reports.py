# api/routes/reports.py
"""
보고서 생성 API
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path
import json

router = APIRouter()

@router.post("/generate")
async def generate_report(request: ReportRequest):
    """보고서 생성"""
    try:
        from report_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        report_data = {
            "start_time": request.start_time,
            "end_time": request.end_time,
            "type": request.report_type
        }
        
        # 보고서 생성
        report_file = await generator.generate(
            report_data,
            format=request.format
        )
        
        return {
            "success": True,
            "report_file": str(report_file),
            "download_url": f"/api/reports/download/{report_file.name}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_report(filename: str):
    """보고서 다운로드"""
    try:
        report_file = Path(f"./reports/{filename}")
        
        if not report_file.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        return FileResponse(
            path=report_file,
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_reports():
    """생성된 보고서 목록"""
    try:
        reports_dir = Path("./reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        reports = []
        for file in reports_dir.glob("*"):
            if file.is_file():
                reports.append({
                    "filename": file.name,
                    "size": file.stat().st_size,
                    "created": datetime.fromtimestamp(file.stat().st_ctime).isoformat()
                })
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

