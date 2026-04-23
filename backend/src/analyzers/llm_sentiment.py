"""
LLM 情感分析服务（OpenAI 兼容接口）

支持 MiniMax、GLM、DeepSeek、Qwen、Claude 等任何 OpenAI 兼容 API。
通过 SENTIMENT_API_BASE / SENTIMENT_API_KEY / SENTIMENT_MODEL 配置。

批量处理：每次调用分析 SENTIMENT_BATCH_SIZE 条文本，减少 API 调用次数。
"""
from __future__ import annotations

import json
import logging
from typing import List

from src.models.note import EmotionType, SentimentLabel, SentimentResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是小红书社交媒体内容情感分析专家。

分析给定的文本列表，按顺序返回 JSON 数组，每项包含：
- label: "positive"（正面）/ "negative"（负面）/ "neutral"（中性）
- score: 置信度，0.0-1.0
- emotion: "joy"（喜悦）/ "anger"（愤怒）/ "sadness"（悲伤）/ "fear"（恐惧）/ "surprise"（惊讶）/ "neutral"（中性）

规则：
- 理解小红书网络用语："绝了""yyds""裂开""踩雷""绝绝子""好用到哭""后悔没早买"等
- 句式"不是……太……了吧"通常是正面感叹
- "凑合""一般般"归中性
- 只返回 JSON 数组，不要任何解释或 Markdown 代码块
"""


class LLMSentimentService:
    """基于大模型的情感分析，支持任何 OpenAI 兼容 API"""

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
        from src.config import settings

        if not texts:
            return []

        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        prompt = f"分析以下 {len(texts)} 条文本：\n\n{numbered}"

        try:
            client = self._get_client()
            resp = client.chat.completions.create(
                model=settings.SENTIMENT_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.1,
                max_tokens=max(1500, len(texts) * 100),  # 推理模型 think 块需要更多空间
            )
            raw = resp.choices[0].message.content or "[]"
            return self._parse(raw, len(texts))

        except Exception as e:
            logger.error("LLM 情感分析失败，降级规则: %s", e)
            from src.analyzers.senta_service import SentaService
            return SentaService()._rule_based_analysis_batch(texts)

    @staticmethod
    def _parse(raw: str, expected: int) -> List[SentimentResult]:
        """解析 LLM 返回的 JSON，长度不足时用中性补齐"""
        try:
            text = raw.strip()
            # 跳过推理模型的 <think>...</think> 块（MiniMax-M2.7 等）
            if "<think>" in text:
                end = text.rfind("</think>")
                text = text[end + 8:].strip() if end != -1 else text.split("</think>")[-1].strip()
            # 兼容 ```json ... ``` 代码块
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning("LLM 返回非 JSON: %s", raw[:200])
            data = []

        results: List[SentimentResult] = []
        for item in data[:expected]:
            try:
                label = SentimentLabel(item.get("label", "neutral"))
                emotion = EmotionType(item.get("emotion", "neutral"))
                score = float(item.get("score", 0.5))
                results.append(SentimentResult(label=label, score=score, emotion=emotion))
            except (ValueError, KeyError):
                results.append(_neutral())

        # 补齐（防止 LLM 少返回）
        while len(results) < expected:
            results.append(_neutral())

        return results


def _neutral() -> SentimentResult:
    return SentimentResult(
        label=SentimentLabel.NEUTRAL,
        score=0.5,
        emotion=EmotionType.NEUTRAL,
    )
