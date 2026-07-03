"""
KOL 挖掘 API 路由
"""
import csv
import io
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.models.kol import KolCandidate
from src.services.kol_discovery import kol_discovery

router = APIRouter()


@router.get("/candidates", response_model=List[KolCandidate])
async def list_candidates(
    min_notes: int = Query(2, ge=1),
    keyword: Optional[str] = None,
    min_engagement: float = Query(0.0, ge=0),
    sentiment: Optional[str] = Query(None, description="positive"),
    hide_own: bool = True,
    hide_competitor: bool = False,
    status: Optional[str] = Query(None, description="candidate/shortlisted/rejected"),
    limit: int = Query(100, ge=1, le=500),
):
    """挖掘 KOL 候选，支持筛选/排序（按综合分倒序）"""
    return await kol_discovery.discover(
        min_notes=min_notes,
        keyword=keyword,
        min_engagement=min_engagement,
        sentiment=sentiment,
        hide_own=hide_own,
        hide_competitor=hide_competitor,
        status=status,
        limit=limit,
    )


class StatusBody(BaseModel):
    status: str
    remark: Optional[str] = None


@router.post("/{user_id}/status")
async def set_status(user_id: str, body: StatusBody):
    """置候选状态：shortlisted / rejected / candidate"""
    await kol_discovery.set_status(user_id, body.status, body.remark)
    return {"user_id": user_id, "status": body.status}


@router.post("/{user_id}/enrich")
async def enrich(user_id: str):
    """付费富化：补粉丝数等（受每日上限约束，结果缓存）"""
    from src.collectors.tikhub import TikHubError

    try:
        return await kol_discovery.enrich(user_id)
    except RuntimeError as e:  # 触达每日上限
        raise HTTPException(status_code=429, detail=str(e)) from e
    except TikHubError as e:  # 上游失败（如欠费 402）
        raise HTTPException(
            status_code=502, detail=f"TikHub 富化失败（可能欠费或受限）：{e}"
        ) from e


@router.get("/export")
async def export_csv(
    status: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
):
    """导出候选为 CSV"""
    rows = await kol_discovery.discover(status=status, limit=limit)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["昵称", "user_id", "命中词", "发文数", "篇均互动",
         "正面占比", "粉丝数", "综合分", "状态", "备注"]
    )
    for c in rows:
        writer.writerow([
            c.nickname, c.user_id, "/".join(c.keywords_hit), c.note_count,
            c.avg_engagement, c.positive_rate, c.fans_count if c.fans_count is not None
            else "", c.fit_score, c.status.value, c.remark or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kol_candidates.csv"},
    )
