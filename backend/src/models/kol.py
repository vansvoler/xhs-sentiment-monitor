"""
KOL 候选数据模型
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class KolStatus(str, Enum):
    """人工筛选状态"""
    CANDIDATE = "candidate"      # 未处理
    SHORTLISTED = "shortlisted"  # 已加入名单
    REJECTED = "rejected"        # 已排除


class KolCandidate(BaseModel):
    """一个 KOL 候选（聚合指标 + 人工态 + 富化结果）"""
    user_id: str
    nickname: str
    avatar: Optional[str] = None

    # —— 免费聚合指标 ——
    note_count: int                       # 话题下发文数
    keywords_hit: List[str] = []          # 命中的监控词
    avg_engagement: float = 0.0           # 篇均(赞+评+藏)
    positive_rate: float = 0.0            # 正面笔记占比
    avg_sentiment_score: float = 0.5
    last_post_at: Optional[datetime] = None

    # —— 归类 ——
    is_own: bool = False
    is_competitor: bool = False

    # —— 打分 ——
    fit_score: float = 0.0                # 综合分 0-100
    score_breakdown: dict = Field(default_factory=dict)

    # —— 富化后（付费）——
    fans_count: Optional[int] = None
    verified: Optional[bool] = None
    bio: Optional[str] = None
    ip_location: Optional[str] = None
    enriched_at: Optional[datetime] = None

    # —— 人工 ——
    status: KolStatus = KolStatus.CANDIDATE
    remark: Optional[str] = None
