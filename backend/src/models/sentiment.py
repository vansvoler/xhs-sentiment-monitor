"""
情感分析批量请求/响应模型 + 负面舆情条目
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from src.models.note import AuthorInfo, SentimentResult

__all__ = [
    "SentimentResult",
    "BatchSentimentRequest",
    "BatchSentimentResponse",
    "NegativeItem",
    "NegativeStatusRequest",
]


class BatchSentimentRequest(BaseModel):
    """批量情感分析请求"""
    texts: List[str]

    class Config:
        json_schema_extra = {
            "example": {"texts": ["这个产品真的很好用", "质量太差了"]}
        }


class BatchSentimentResponse(BaseModel):
    """批量情感分析响应"""
    results: List[SentimentResult]
    total: int
    processing_time: float


class NegativeItem(BaseModel):
    """负面舆情条目：笔记与评论统一成同构结构，供工作台处置"""
    kind: str                           # note | comment
    id: str                             # note_id / comment_id
    note_id: str                        # 所属笔记（评论挂父笔记）
    title: str                          # 笔记标题 / 评论所属笔记标题
    excerpt: str                        # 正文 / 评论内容
    author: AuthorInfo
    sentiment: SentimentResult
    keyword: Optional[str] = None       # 命中的监控词
    category: Optional[str] = None      # brand / competitor / industry
    happened_at: datetime               # 笔记发布时间 / 评论时间
    likes: int = 0
    url: str                            # 小红书原文链接
    handle_status: str = "open"         # open / handled


class NegativeStatusRequest(BaseModel):
    """负面条目处置状态变更"""
    status: str                         # open / handled
