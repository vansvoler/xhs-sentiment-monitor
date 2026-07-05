"""
系统配置管理
"""
from typing import Dict, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """系统配置"""

    # ---------- 服务 ----------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # ---------- 数据库 ----------
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "xhs_sentiment"

    # ---------- Redis ----------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---------- TikHub API ----------
    TIKHUB_BASE_URL: str = "https://api.tikhub.dev"           # 主域名
    TIKHUB_FALLBACK_BASE_URL: str = "https://api.tikhub.io"   # 400/502/504 时切换
    TIKHUB_TOKEN: str = ""
    TIKHUB_REQUEST_TIMEOUT_SECONDS: int = 15

    # ---------- 采集 ----------
    COLLECT_INTERVAL_MINUTES: int = 30
    MAX_NOTES_PER_PAGE: int = 20  # TikHub 一页固定 20 条
    # 评论采集是 TikHub 额度大头，以下三项控制成本：
    MAX_COMMENTS_PER_NOTE: int = 20   # 每篇只拉头部 1 页，足够看舆情
    COMMENTS_REFRESH_HOURS: int = 48  # 评论变化慢，刷新间隔放长
    COMMENT_MAX_AGE_DAYS: int = 14    # 只给近 N 天发布的笔记拉评论，老笔记不反复烧

    # ---------- 监控目标 ----------
    MONITOR_KEYWORDS: List[str] = []   # 已废弃，保留向后兼容
    MONITOR_TAGS: List[str] = []
    COMPETITORS: List[str] = []        # 已废弃，保留向后兼容

    # 三模块关键词（推荐使用）
    MONITOR_KEYWORDS_BRAND: List[str] = []
    MONITOR_KEYWORDS_COMPETITOR: List[str] = []
    MONITOR_KEYWORDS_INDUSTRY: List[str] = []

    @property
    def keyword_category_map(self) -> Dict[str, str]:
        """返回 {keyword: category} 映射，同一词出现在多组时取首个分类"""
        result: Dict[str, str] = {}
        for kw in self.MONITOR_KEYWORDS_BRAND:
            result.setdefault(kw, "brand")
        for kw in self.MONITOR_KEYWORDS_COMPETITOR:
            result.setdefault(kw, "competitor")
        for kw in self.MONITOR_KEYWORDS_INDUSTRY:
            result.setdefault(kw, "industry")
        return result

    @property
    def all_keywords(self) -> List[str]:
        """去重后的全部关键词列表（含旧版 MONITOR_KEYWORDS）"""
        seen: set[str] = set()
        out: List[str] = []
        for kw in (
            self.MONITOR_KEYWORDS_BRAND
            + self.MONITOR_KEYWORDS_COMPETITOR
            + self.MONITOR_KEYWORDS_INDUSTRY
            + self.MONITOR_KEYWORDS
        ):
            if kw not in seen:
                seen.add(kw)
                out.append(kw)
        return out

    # ---------- 情感分析 ----------
    # provider: llm | senta | rule
    SENTIMENT_PROVIDER: str = "rule"
    # LLM provider 配置（任何 OpenAI 兼容接口）
    SENTIMENT_API_BASE: str = "https://api.minimax.chat/v1"
    SENTIMENT_API_KEY: str = ""
    SENTIMENT_MODEL: str = "MiniMax-Text-01"
    SENTIMENT_BATCH_SIZE: int = 20
    # 每轮分析的上限（循环抽干积压，但设天花板防止单轮 LLM 调用过多）
    SENTIMENT_MAX_PER_RUN: int = 400
    SENTIMENT_CACHE_TTL: int = 3600

    # ---------- 舆情预警 ----------
    # 负面笔记/评论触发实时告警的最低情感置信度
    ALERT_NEGATIVE_SCORE_MIN: float = 0.6
    # 作者粉丝数达到该值视为"高影响力"，负面时升级为 critical
    ALERT_HIGH_INFLUENCE_FANS: int = 10000
    # 关键词负面率告警阈值（窗口内负面占比超过即告警）
    ALERT_NEGATIVE_RATE_THRESHOLD: float = 0.3
    # 声量突增告警：窗口声量 / 上一窗口声量 超过该倍数
    ALERT_SPIKE_RATIO: float = 2.0
    # 关键词健康扫描的时间窗口（小时）
    ALERT_SCAN_HOURS: int = 24
    # 关键词需达到该最小声量才评估负面率/突增（避免小样本噪声）
    ALERT_MIN_VOLUME: int = 5
    # 关键词健康扫描周期（分钟）
    ALERT_SCAN_INTERVAL_MINUTES: int = 30

    # ---------- KOL 挖掘 ----------
    # 昵称含这些词的账号判定为"自家"，从候选池排除
    KOL_OWN_ACCOUNT_MARKERS: List[str] = ["渊学通", "英通"]
    # 富化（get_user_info）每日调用上限，防止付费失控
    KOL_ENRICH_DAILY_LIMIT: int = 100

    # ---------- WebSocket ----------
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
