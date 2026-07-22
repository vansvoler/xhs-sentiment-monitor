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
    # 每天北京时间几点跑一次采集+分析+告警（一天一次，控制 TikHub 成本）
    DAILY_COLLECT_HOUR: int = 8
    COLLECT_INTERVAL_MINUTES: int = 240  # 仅评论采集（已关停）仍引用
    MAX_NOTES_PER_PAGE: int = 20  # TikHub 一页固定 20 条
    # 各分类每次抓几页（1 页=20 条=1 次调用）。行业词热度高抓 2 页，品牌/竞品 1 页够。
    SEARCH_PAGES_BY_CATEGORY: Dict[str, int] = {
        "brand": 1,
        "competitor": 1,
        "industry": 2,
    }
    # general（综合/热门）排序补抓页数：与时间流是两个不同的结果集，互补采样
    # （时间流会漏排序靠后的真实用户帖，如求避雷/比价帖）。
    # 只补品牌词——本品牌口碑不容漏；竞品词时间流够用，行业词热帖噪声大。
    SEARCH_GENERAL_PAGES_BY_CATEGORY: Dict[str, int] = {
        "brand": 1,
        "competitor": 0,
        "industry": 0,
    }
    # 搜索排序：time_descending=最新优先（抓新舆情）；general=综合/热门
    # 注：小红书 app 搜索接口不保证严格按时间返回，偶尔混排老的高互动帖，
    # 故用 SEARCH_MAX_AGE_DAYS 在入库时兜底，只留近期笔记。
    SEARCH_SORT_TYPE: str = "time_descending"
    # 入库前只留标题/正文/标签真正含关键词的笔记（过滤模糊/同音匹配噪声）
    SEARCH_REQUIRE_KEYWORD_MATCH: bool = True
    # 入库前丢弃发布超过 N 天的老笔记（0=不限制）。防接口混排把一年前的帖捞进来。
    SEARCH_MAX_AGE_DAYS: int = 180
    MAX_COMMENTS_PER_NOTE: int = 20  # 每篇只拉头部 1 页，足够看舆情
    # 评论采集总开关：小红书评论接口 $0.01/次（普通接口 10 倍），太贵已关停；
    # 现有评论数据仍照常展示，只是不再新增。需要时置 True 恢复。
    ENABLE_COMMENT_COLLECTION: bool = False
    # 评论抓取的分类（品牌/竞品/行业全抓，规则一致）
    COMMENT_CATEGORIES: List[str] = ["brand", "competitor", "industry"]
    # 笔记采集满 N 小时后才拉评论（给评论累积时间），采一次不刷新
    COMMENT_DELAY_HOURS: int = 24
    # 评论数低于该值的笔记不拉评论（省调用，零评论没舆情可看）
    COMMENT_MIN_COMMENTS: int = 1

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
    # 相关性判定的领域背景（帮 LLM 区分同名异物，如"犀牛"=教育机构而非动物）
    SENTIMENT_DOMAIN_CONTEXT: str = "国际教育（A-Level/IB/AP/雅思/留学等培训机构）"
    # 监控词的真实指代（帮 LLM 精确判相关性）：裸词有歧义时补上它到底指谁。
    # 只列当前在 monitor_keywords 里的词——失效的 hint 会误导人以为该词还在采集。
    #
    # 教训：过短的缩写（"yxt"）救不回来。它同时是歌手姚晓棠的粉丝缩写、游戏代肝
    # 黑话、骑行俱乐部、墨水屏阅读器品牌，121 篇里只有零星几条真的关于渊学通，
    # 且否定式 hint（"非其他 yxt"）对 LLM 无效——它无法穷举不是哪些。该词已删除。
    SENTIMENT_KEYWORD_HINTS: Dict[str, str] = {
        "渊学通": "国际教育培训机构『渊学通』（英文简称 yxt）",
        "唯寻": "国际教育培训机构『唯寻国际教育』",
        "澜大": "国际教育培训机构『澜大教育』，非兰州大学",
    }
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
