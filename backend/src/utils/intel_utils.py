"""统一情报项辅助函数。

`infer_impact_targets` 汇合了 UCAS 与大学官网两条链路里原本各写一遍的关键词规则，
覆盖中英文常见招生/签证/奖学金术语。`services/intel_feed.py` 里另有一份针对小红书
笔记域的同名函数，规则不同，因此不在此处合并。
"""

from __future__ import annotations


def infer_impact_targets(title: str, content: str) -> list[str]:
    """从标题和摘要推断影响对象，覆盖 UCAS / 海外大学官网 / 政策类信源。"""

    raw = f"{title} {content}"
    lower = raw.lower()
    targets: list[str] = []

    if "本科" in raw or "undergraduate" in lower:
        targets.append("本科")
    if "硕士" in raw or "postgraduate" in lower:
        targets.append("硕士")
    if (
        "申请" in raw
        or "admission" in lower
        or "application" in lower
        or "apply" in lower
        or "deadline" in lower
    ):
        targets.append("申请季")
    if "签证" in raw or "visa" in lower:
        targets.append("签证")
    if (
        "奖学金" in raw
        or "scholarship" in lower
        or "funding" in lower
        or "fee waiver" in lower
    ):
        targets.append("奖学金")

    return targets
