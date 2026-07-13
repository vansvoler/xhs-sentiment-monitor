"""
LLM 情感分析服务（OpenAI 兼容接口）

支持 MiniMax、GLM、DeepSeek、Qwen、Claude 等任何 OpenAI 兼容 API。
通过 SENTIMENT_API_BASE / SENTIMENT_API_KEY / SENTIMENT_MODEL 配置。

批量处理：每次调用分析 SENTIMENT_BATCH_SIZE 条文本，减少 API 调用次数。
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional, Tuple

from src.models.note import EmotionType, SentimentLabel, SentimentResult

logger = logging.getLogger(__name__)

_SENTIMENT_RULES = """\
情感判定站在【国际教育品牌舆情】视角：衡量的是"对教育机构/品牌/赛道口碑的影响"，
而非文字表面的情绪。核心原则：负面情绪 ≠ 负面舆情——没有明确评价对象的个人情绪一律中性。

label 取值：
- "negative"（负面舆情）：满足任一即是——
  · 对可指认的机构/品牌/老师/课程/服务的差评、投诉、避雷、退费纠纷；
  · 唱衰或劝退整条赛道/品类（如"别碰国际学校""留学就是天坑"）；
  · 涉及竞品的负面或偏负面提及（从宽）。
- "positive"（正面）：对机构/品牌/课程的好评、安利、成功案例，或机构自身的正向招生营销。
- "neutral"（中性）：不构成口碑影响的内容——
  · 考生个人情绪：考试焦虑、备考压力、成绩失落（"好紧张""好难""下辈子不考了"）；
  · 学习日常/Vlog、玩梗调侃（"坐牢""脱产""stole my soul""屠鸭"）；
  · 经验贴、备考攻略、教学干货、知识科普、采访问答；
  · 求助提问、找老师、报班咨询；纯费用调侃且无明确机构指向。

情绪与网络用语（辅助判断，不改变上面的舆情口径）：
- "绝了""yyds""好用到哭""后悔没早买"多为正面；"踩雷""避雷""无语""退费""水"常指向机构差评；
- 句式"不是……太……了吧"通常是正面感叹；"凑合""一般般"归中性。

字段：
- score: 置信度，0.0-1.0
- emotion: "joy"（喜悦）/ "anger"（愤怒）/ "sadness"（悲伤）/ "fear"（恐惧）/ "surprise"（惊讶）/ "neutral"（中性）
- 只返回 JSON 数组，不要任何解释或 Markdown 代码块
"""

_SYSTEM_PROMPT = f"""\
你是小红书社交媒体内容情感分析专家。

分析给定的文本列表，按顺序返回 JSON 数组，每项包含 label / score / emotion。

{_SENTIMENT_RULES}"""


def _relevance_prompt(domain: str) -> str:
    return f"""\
你是小红书社交媒体舆情分析专家。监控领域：{domain}。

输入是编号列表，每条格式为 `[监控词: xxx（指代说明）] 文本`。
括号里是该监控词真正指代的对象；没有括号时按字面理解。
按顺序返回 JSON 数组，每项包含 relevant / label / score / emotion。

相关性字段 relevant: true/false —— 文本是否真的在谈论监控词所指代的那个具体对象。
判 false 的典型情况：
- 同名异物：撞名的动物/影视/地名/其他行业（如"犀牛"指动物、"澜大"指兰州大学）。
- 同字不同物：名字里含该词的另一个产品/机构（如监控"学通"时的"师学通"）。
- 纯谐音蹭词、与指代对象毫无实质关联。
只要不是指代说明里那个对象，一律 false，宁缺毋滥。

{_SENTIMENT_RULES}"""


class LLMSentimentService:
    """基于大模型的情感分析，支持任何 OpenAI 兼容 API"""

    # 笔记分析可顺带判定与监控词的语义相关性（零额外调用）
    supports_relevance = True

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            from src.config import settings

            self._client = OpenAI(
                api_key=settings.SENTIMENT_API_KEY,
                base_url=settings.SENTIMENT_API_BASE,
            )
        return self._client

    def batch_analyze(self, texts: List[str]) -> List[SentimentResult]:
        """纯情感分析（评论等无监控词上下文的文本）"""
        return [r for r, _ in self._analyze(texts, None)]

    def batch_analyze_notes(
        self, texts: List[str], keywords: List[str]
    ) -> List[Tuple[SentimentResult, bool]]:
        """笔记分析：情感 + 与监控词的语义相关性，一次调用同时产出"""
        return self._analyze(texts, keywords)

    def _analyze(
        self, texts: List[str], keywords: Optional[List[str]]
    ) -> List[Tuple[SentimentResult, bool]]:
        from src.config import settings

        if not texts:
            return []

        if keywords is None:
            system = _SYSTEM_PROMPT
            numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        else:
            system = _relevance_prompt(settings.SENTIMENT_DOMAIN_CONTEXT)
            hints = settings.SENTIMENT_KEYWORD_HINTS

            def _kw_label(kw: str) -> str:
                hint = hints.get(kw)
                return f"{kw}（指{hint}）" if hint else kw

            numbered = "\n".join(
                f"{i+1}. [监控词: {_kw_label(kw)}] {t}"
                for i, (t, kw) in enumerate(zip(texts, keywords))
            )
        prompt = f"分析以下 {len(texts)} 条文本：\n\n{numbered}"

        try:
            client = self._get_client()
            resp = client.chat.completions.create(
                model=settings.SENTIMENT_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.1,
                max_tokens=max(1500, len(texts) * 100),  # 推理模型 think 块需要更多空间
            )
            raw = resp.choices[0].message.content or "[]"
            return self._parse(raw, len(texts))

        except Exception as e:
            logger.error("LLM 情感分析失败，降级规则: %s", e)
            from src.analyzers.sentiment_service import SentaService
            results = SentaService()._rule_based_analysis_batch(texts)
            return [(r, True) for r in results]  # 规则无法判相关性，默认相关

    @staticmethod
    def _parse(raw: str, expected: int) -> List[Tuple[SentimentResult, bool]]:
        """解析 LLM 返回的 JSON，长度不足时用（中性, 相关）补齐"""
        try:
            data = json.loads(_extract_json_payload(raw))
        except ValueError as e:  # json.JSONDecodeError 是 ValueError 的子类
            # 打印长度与首尾片段，用于区分「被文字/围栏包裹」和「被 max_tokens 截断」：
            # tail 以 ] 收尾说明内容完整，停在半个对象上则是真截断。
            logger.warning(
                "LLM 返回无法解析（%s）: len=%d head=%r tail=%r",
                e, len(raw), raw[:120], raw[-120:],
            )
            data = []

        # expected == 1 时模型偶尔直接回对象而非数组，包一层避免后续切片崩溃
        if isinstance(data, dict):
            data = [data]

        results: List[Tuple[SentimentResult, bool]] = []
        for item in data[:expected]:
            try:
                label = SentimentLabel(item.get("label", "neutral"))
                emotion = EmotionType(item.get("emotion", "neutral"))
                score = float(item.get("score", 0.5))
                relevant = bool(item.get("relevant", True))
                sentiment = SentimentResult(label=label, score=score, emotion=emotion)
                results.append((sentiment, relevant))
            except (ValueError, KeyError, TypeError, AttributeError):
                results.append((_neutral(), True))

        # 补齐（防止 LLM 少返回）
        while len(results) < expected:
            results.append((_neutral(), True))

        return results


# 最外层 JSON 结构的开闭括号对
_BRACKETS = {"[": "]", "{": "}"}


def _extract_json_payload(raw: str) -> str:
    """从 LLM 原始输出里抠出最外层 JSON 数组（或对象）。

    与其为「代码围栏」「前置说明文字」「大小写标签」各写一个分支，
    不如直接定位最外层括号 —— 所有包装方式一并消失。

    失败时抛 ValueError，异常文案即诊断结论（截断 / 无 JSON）。
    """
    text = raw.strip()

    # 推理模型（MiniMax-M2.7 等）把思维链内联在 content 里。
    # think 块内部可能出现 [ ]，必须先剥离，否则会把思维链当成答案解析。
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1].strip()
    elif "<think>" in text:
        raise ValueError("<think> 未闭合，正文在思维链中途被 max_tokens 截断")

    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not starts:
        raise ValueError("未找到 JSON 数组或对象")

    start = min(starts)
    end = text.rfind(_BRACKETS[text[start]])
    if end <= start:
        raise ValueError("JSON 结构未闭合，疑似被 max_tokens 截断")

    return text[start : end + 1]


def _neutral() -> SentimentResult:
    return SentimentResult(
        label=SentimentLabel.NEUTRAL,
        score=0.5,
        emotion=EmotionType.NEUTRAL,
    )
