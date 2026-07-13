"""
读侧共享查询过滤器

笔记的 ``relevance`` 由情感分析任务顺带判定（LLM 语义级）：
- ``on_topic``  真正在谈论监控词指代的品牌/机构/话题
- ``off_topic`` 同名异物/谐音蹭词等语义噪声

所有读侧（列表/统计/趋势/竞品/告警/KOL）统一用 ``ON_TOPIC`` 排除噪声；
尚未判定（字段缺失）的笔记视为相关，等待下一轮分析补齐。
"""
from typing import Any, Dict

ON_TOPIC: Dict[str, Any] = {"relevance": {"$ne": "off_topic"}}
