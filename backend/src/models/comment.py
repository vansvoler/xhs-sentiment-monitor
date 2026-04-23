"""
评论数据模型
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models.note import AuthorInfo, SentimentResult


class Comment(BaseModel):
    """评论"""
    id: Optional[str] = None
    comment_id: str
    note_id: str
    content: str
    author: AuthorInfo
    likes: int = 0
    replies: List["Comment"] = []
    created_at: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    sentiment: Optional[SentimentResult] = None

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": "789012",
                "note_id": "66d3b9a0000000001a030000",
                "content": "真的很不错！",
                "author": {
                    "user_id": "789012",
                    "nickname": "评论用户",
                    "avatar": "https://...",
                    "fans_count": 500,
                },
                "likes": 50,
                "replies": [],
                "created_at": "2024-01-01T01:00:00Z",
                "sentiment": {"label": "positive", "score": 0.90, "emotion": "joy"},
            }
        }
