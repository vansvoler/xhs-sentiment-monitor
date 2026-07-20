"""
笔记相关数据模型
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ================ 枚举 ================
class SentimentLabel(str, Enum):
    """情感标签"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class EmotionType(str, Enum):
    """情绪类型"""
    ANGER = "anger"
    JOY = "joy"
    SADNESS = "sadness"
    FEAR = "fear"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"


class NoteType(str, Enum):
    """笔记类型"""
    NORMAL = "normal"   # 图文
    VIDEO = "video"     # 视频
    LIVE = "live"       # 直播


# ================ 嵌套结构 ================
class SentimentResult(BaseModel):
    """情感分析结果"""
    label: SentimentLabel
    score: float = Field(ge=0, le=1)
    emotion: EmotionType


class AuthorInfo(BaseModel):
    """作者信息"""
    user_id: str
    nickname: str
    avatar: Optional[str] = None
    fans_count: int = 0


class MediaInfo(BaseModel):
    """媒体信息"""
    type: str = "image"                 # image | video
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None      # 视频时长(秒)


class StatsInfo(BaseModel):
    """互动统计"""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    collects: int = 0


# ================ 主模型 ================
class Note(BaseModel):
    """笔记"""
    id: Optional[str] = None
    note_id: str
    title: str
    content: str
    type: NoteType = NoteType.NORMAL
    author: AuthorInfo
    media: List[MediaInfo] = []
    tags: List[str] = []
    stats: StatsInfo
    published_at: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    comments_collected_at: Optional[datetime] = None
    sentiment: Optional[SentimentResult] = None
    keywords: List[str] = []
    category: Optional[str] = None       # 分类：竞品/话题等
    search_keyword: Optional[str] = None  # 命中的监控词（采集时的搜索词）
    relevance: Optional[str] = None      # on_topic / off_topic（LLM 语义判定）
    xsec_token: Optional[str] = None     # TikHub web 搜索结果带

    class Config:
        json_schema_extra = {
            "example": {
                "note_id": "66d3b9a0000000001a030000",
                "title": "产品使用心得分享",
                "content": "这个产品真的很好用...",
                "type": "normal",
                "author": {
                    "user_id": "123456",
                    "nickname": "用户昵称",
                    "avatar": "https://...",
                    "fans_count": 10000,
                },
                "media": [],
                "tags": ["产品测评", "好物推荐"],
                "stats": {"likes": 1000, "comments": 200, "shares": 50, "collects": 300},
                "published_at": "2024-01-01T00:00:00Z",
                "sentiment": {"label": "positive", "score": 0.85, "emotion": "joy"},
                "keywords": ["好用", "推荐"],
                "category": "产品",
            }
        }


class TrendData(BaseModel):
    """趋势数据"""
    timestamp: datetime
    positive_count: int
    negative_count: int
    neutral_count: int
    total_notes: int
    total_comments: int
    avg_sentiment_score: float
    hot_keywords: List[str]


class CompetitorData(BaseModel):
    """竞品数据（含本品牌对照）"""
    name: str
    note_count: int
    avg_sentiment_score: float
    positive_count: int
    negative_count: int
    total_mentions: int
    is_own: bool = False               # 本品牌标记（品牌词组聚合）
