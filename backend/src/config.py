"""
系统配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Dict


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
    MAX_COMMENTS_PER_NOTE: int = 100
    COMMENTS_REFRESH_HOURS: int = 6  # 每条笔记评论刷新间隔

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
    SENTIMENT_CACHE_TTL: int = 3600

    # ---------- WebSocket ----------
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
