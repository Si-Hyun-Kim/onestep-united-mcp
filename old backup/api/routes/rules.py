# api/routes/rules.py
"""
룰 관련 API
"""

from fastapi import APIRouter, HTTPException
import sys
sys.path.append('../../mcp_server')
from rule_manager import SuricataRuleManager

router = APIRouter()
rule_manager = SuricataRuleManager()

@router.get("/active")
async def get_active_rules(category: str = "all"):
    """활성 룰 목록"""
    try:
        rules = await rule_manager.get_active_rules(category)
        return {
            "success": True,
            "category": category,
            "count": len(rules),
            "rules": rules
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add")
async def add_rule(request: RuleRequest):
    """룰 추가"""
    try:
        result = await rule_manager.add_rule(
            request.rule_content,
            request.description,
            request.auto_reload
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{sid}")
async def delete_rule(sid: int):
    """룰 삭제"""
    try:
        result = await rule_manager.remove_rule(sid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_rule(rule_content: str):
    """룰 유효성 검증"""
    try:
        result = await rule_manager.validate_rule(rule_content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))