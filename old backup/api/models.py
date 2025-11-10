# api/models.py
"""
API 데이터 모델
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class LogQuery(BaseModel):
    count: int = Field(default=50, ge=1, le=1000)
    severity: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class RuleRequest(BaseModel):
    rule_content: str
    description: Optional[str] = None
    auto_reload: bool = True

class BlockIPRequest(BaseModel):
    ip: str
    reason: str = "Security threat"
    duration: int = 0  # 0 = 영구

class UnblockIPRequest(BaseModel):
    ip: str

class ReportRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    report_type: str = "summary"  # summary, detailed, executive
    format: str = "pdf"  # pdf, html, json

class WebSocketManager:
    """WebSocket 연결 관리"""
    
    def __init__(self):
        self.active_connections: List = []
    
    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket):
        self.active_connections.remove(websocket)
    
    async def send_personal(self, message: str, websocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)