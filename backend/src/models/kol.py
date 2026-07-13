"""
KOL 候选数据模型
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class KolStatus(str, Enum):
    """人工筛选状态

    ``rejected`` 是人工的最后一道闸：自动规则再准也会放进完全无关的人
    （如同名异物的关键词捞来的追星号），排除后从默认视图消失，但保留在
    "已排除" tab 里可随时恢复——是隐藏，不是删除。
    """
    CANDIDATE = "candidate"      # 未处理
    SHORTLISTED = "shortlisted"  # 已加入名单
    REJECTED = "rejected"        # 已排除（默认视图不显示）


class AccountType(str, Enum):
    """账号身份

    按昵称是否含品牌词/竞品词判定：机构官号与员工号会把机构名写进昵称
    （如 ``渊学通-常州`` ``潘潘在唯寻``），这是高精度低召回的信号。判不出的
    一律归 ``individual``——宁可让矩阵号混进候选池等人工过目，也不能把真素人
    误杀。签约关系无法从公开数据推断，不做猜测。
    """
    OWN_MATRIX = "own_matrix"                # 自家官号/员工号
    COMPETITOR_MATRIX = "competitor_matrix"  # 竞品官号/员工号
    INDIVIDUAL = "individual"                # 第三方素人/垂类作者


class KolCandidate(BaseModel):
    """一个 KOL 候选（聚合指标 + 人工态 + 富化结果）"""
    user_id: str
    nickname: str
    avatar: Optional[str] = None

    # —— 免费聚合指标 ——
    note_count: int                       # 话题下发文数
    keywords_hit: List[str] = []          # 命中的监控词
    top_category: str = "industry"        # 命中词里最近的一类 brand>competitor>industry
    avg_engagement: float = 0.0           # 篇均(赞+评+藏)
    last_post_at: Optional[datetime] = None

    # —— 情感（仅展示，不参与打分）——
    positive_rate: float = 0.0
    avg_sentiment_score: float = 0.5

    # —— 归类 ——
    account_type: AccountType = AccountType.INDIVIDUAL
    account_type_manual: bool = False     # 分类是否被人工校正过

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


class KolNote(BaseModel):
    """候选作者名下命中监控词的一篇笔记——分数的原始依据，供人工过目"""
    note_id: str
    xsec_token: Optional[str] = None
    title: str = ""
    search_keyword: str = ""
    published_at: Optional[datetime] = None
    likes: int = 0
    comments: int = 0
    collects: int = 0
    sentiment: Optional[str] = None
