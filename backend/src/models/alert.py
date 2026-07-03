"""
舆情预警数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AlertType(str, Enum):
    """告警类型"""
    NEGATIVE_NOTE = "negative_note"        # 单条负面笔记
    NEGATIVE_COMMENT = "negative_comment"  # 单条负面评论
    NEGATIVE_RATE = "negative_rate"        # 关键词负面率超阈值
    VOLUME_SPIKE = "volume_spike"          # 关键词声量突增


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """处理状态"""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"


class Alert(BaseModel):
    """一条舆情告警"""
    alert_id: str                              # 去重键，同一事件只入库一次
    type: AlertType
    level: AlertLevel
    title: str
    message: str
    keyword: Optional[str] = None              # 关联监控词
    note_id: Optional[str] = None              # 关联笔记
    sentiment_score: Optional[float] = None
    metric: Dict[str, Any] = Field(default_factory=dict)  # 负面率/声量等指标快照
    status: AlertStatus = AlertStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
