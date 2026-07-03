"""
统一运营情报数据模型
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IntelSourceType(str, Enum):
    """统一来源类型"""

    XIAOHONGSHU = "xiaohongshu"
    UCAS = "ucas"
    UNIVERSITY_SITE = "university_site"
    EXAM_BOARD = "exam_board"
    VISA_POLICY = "visa_policy"
    WECHAT_MEDIA = "wechat_media"


class IntelSourceSyncStatus(str, Enum):
    """来源同步状态。"""

    SUCCESS = "success"
    BLOCKED = "blocked"
    ERROR = "error"


class IntelItem(BaseModel):
    """统一情报项"""

    item_id: str
    source_type: IntelSourceType
    source_name: str
    title: str
    summary_short: str
    summary_long: str
    impact_targets: list[str] = Field(default_factory=list)
    published_at: datetime
    collected_at: datetime
    original_url: str
    priority_hint: str | None = None
    school_name: str | None = None
    source_group: str | None = None
    external_id: str | None = None
    content_html: str | None = None


class IntelOverviewSection(BaseModel):
    """总览页来源分区"""

    source_key: str
    source_label: str
    total_items: int
    preview_items: list[IntelItem]


class IntelHelperRail(BaseModel):
    """右侧轻辅助栏"""

    highlight_count: int
    top_counts: dict[str, int]


class IntelSourceSyncReport(BaseModel):
    """单个来源的一次同步结果。"""

    source_id: str
    source_type: IntelSourceType
    source_name: str
    school_name: str | None = None
    status: IntelSourceSyncStatus
    item_count: int = 0
    error_message: str | None = None
    notes: str | None = None
    synced_at: datetime
