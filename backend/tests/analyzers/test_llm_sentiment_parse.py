"""
LLM 情感分析：JSON 解析健壮性测试

全部离线，不触发任何 LLM / TikHub 真实调用。
覆盖三类现场输入：干净数组 / Markdown 围栏包裹 / 被 max_tokens 截断。
"""
from __future__ import annotations

import pytest

from src.analyzers.llm_sentiment import (
    LLMSentimentService,
    _extract_json_payload,
)
from src.models.note import EmotionType, SentimentLabel

# ---------------------------------------------------------------- 样例数据

_ITEM = '{"relevant": true, "label": "negative", "score": 0.8, "emotion": "fear"}'
_ARRAY = f"[{_ITEM}]"


def _parse(raw: str, expected: int = 1):
    return LLMSentimentService._parse(raw, expected)


# ---------------------------------------------------------- _extract_json_payload


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(_ARRAY, id="干净数组"),
        pytest.param(f"```json\n{_ARRAY}\n```", id="小写围栏"),
        pytest.param(f"```JSON\n{_ARRAY}\n```", id="大写围栏"),
        pytest.param(f"```\n{_ARRAY}\n```", id="无标签围栏"),
        pytest.param(f"以下是分析结果：\n```json\n{_ARRAY}\n```", id="围栏前有文字"),
        pytest.param(f"{_ARRAY}\n\n希望对你有帮助！", id="数组后有文字"),
        pytest.param(f"<think>先看第 [1] 条…</think>\n{_ARRAY}", id="think含方括号"),
    ],
)
def test_extract_recovers_clean_array(raw: str) -> None:
    """各种包装方式都应还原出同一个数组"""
    assert _extract_json_payload(raw) == _ARRAY


def test_extract_unterminated_think_block_reports_truncation() -> None:
    """think 块没闭合 = 正文还没生成就被截断，异常文案要点明 max_tokens"""
    with pytest.raises(ValueError, match="max_tokens"):
        _extract_json_payload("<think>让我逐条分析，第一条看起来是负面的")


def test_extract_truncated_array_reports_truncation() -> None:
    """数组缺右括号 = 真截断"""
    with pytest.raises(ValueError, match="未闭合"):
        _extract_json_payload(f"[{_ITEM},{{")


def test_extract_no_json_at_all() -> None:
    with pytest.raises(ValueError, match="未找到 JSON"):
        _extract_json_payload("抱歉，我无法分析这些内容。")


# ------------------------------------------------------------------- _parse


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(_ARRAY, id="干净数组"),
        pytest.param(f"```json\n{_ARRAY}\n```", id="markdown围栏"),
        pytest.param(f"以下是结果：\n```json\n{_ARRAY}\n```", id="围栏前有说明文字"),
        pytest.param(_ITEM, id="单个对象非数组"),
    ],
)
def test_parse_reads_fields(raw: str) -> None:
    """能解析出的输入，字段必须如实还原，不得静默降级为中性"""
    (sentiment, relevant), = _parse(raw, expected=1)

    assert sentiment.label is SentimentLabel.NEGATIVE
    assert sentiment.score == pytest.approx(0.8)
    assert sentiment.emotion is EmotionType.FEAR
    assert relevant is True


def test_parse_honors_relevant_false() -> None:
    raw = (
        '[{"relevant": false, "label": "neutral",'
        ' "score": 0.5, "emotion": "neutral"}]'
    )
    (_, relevant), = _parse(raw, expected=1)
    assert relevant is False


def test_parse_truncated_falls_back_to_neutral(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """截断输入无法解析：补齐为（中性, 相关），并打出带 len/tail 的诊断日志"""
    truncated = f"[{_ITEM},{{"

    results = _parse(truncated, expected=2)

    assert len(results) == 2
    assert all(s.label is SentimentLabel.NEUTRAL and rel for s, rel in results)
    assert "无法解析" in caplog.text
    assert f"len={len(truncated)}" in caplog.text


def test_parse_pads_short_response_to_expected() -> None:
    """LLM 少返回时用中性补齐到 expected 条"""
    results = _parse(_ARRAY, expected=3)

    assert len(results) == 3
    assert results[0][0].label is SentimentLabel.NEGATIVE
    assert all(s.label is SentimentLabel.NEUTRAL for s, _ in results[1:])


def test_parse_truncates_overlong_response() -> None:
    """LLM 多返回时按 expected 截断"""
    assert len(_parse(f"[{_ITEM},{_ITEM},{_ITEM}]", expected=2)) == 2


def test_parse_survives_malformed_items() -> None:
    """数组里混入字符串/非法枚举值时，逐条降级而不是整批崩溃"""
    raw = f'["垃圾数据", {{"label": "not_a_label"}}, {_ITEM}]'

    results = _parse(raw, expected=3)

    assert len(results) == 3
    assert results[0][0].label is SentimentLabel.NEUTRAL
    assert results[1][0].label is SentimentLabel.NEUTRAL
    assert results[2][0].label is SentimentLabel.NEGATIVE
