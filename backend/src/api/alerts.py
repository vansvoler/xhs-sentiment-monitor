"""
舆情预警 API 路由
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.services.alert_service import alert_service

router = APIRouter()


@router.get("/")
async def list_alerts(
    status: Optional[str] = Query(None, description="open / acknowledged"),
    level: Optional[str] = Query(None, description="info / warning / critical"),
    limit: int = Query(50, ge=1, le=200),
):
    """获取告警列表，按时间倒序"""
    return await alert_service.list_alerts(status=status, level=level, limit=limit)


@router.post("/scan")
async def scan_now():
    """手动触发一次关键词健康扫描，返回新增告警数"""
    alerts = await alert_service.scan_keyword_health()
    created = await alert_service.emit(alerts)
    return {"detected": len(alerts), "created": created}


@router.post("/{alert_id}/ack")
async def acknowledge(alert_id: str):
    """标记告警为已处理"""
    ok = await alert_service.acknowledge(alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="告警不存在或状态未变更")
    return {"alert_id": alert_id, "status": "acknowledged"}
