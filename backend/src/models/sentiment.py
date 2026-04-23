"""
情感分析批量请求/响应模型
"""
from typing import List

from pydantic import BaseModel

from src.models.note import SentimentResult


__all__ = [
    "SentimentResult",
    "BatchSentimentRequest",
    "BatchSentimentResponse",
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
