"""
TikHub XHS API 客户端

三个固定端点：
  搜索  GET /api/v1/xiaohongshu/app/search_notes
  详情  GET /api/v1/xiaohongshu/web_v2/fetch_feed_notes_v2
  评论  GET /api/v1/xiaohongshu/web_v2/fetch_note_comments

域名 failover：先试 TIKHUB_BASE_URL（api.tikhub.dev），
400/502/504 后切 TIKHUB_FALLBACK_BASE_URL（api.tikhub.io）。
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from src.config import settings

logger = logging.getLogger(__name__)


# ===================================================================
# 异常
# ===================================================================
class TikHubError(Exception):
    """基类"""


class TikHubRetriableError(TikHubError):
    """可重试/可切域名：400 / 502 / 504 / 响应格式异常"""


class TikHubFatalError(TikHubError):
    """致命：401 / 403，换域名也没用"""


# ===================================================================
# 工具函数（纯函数，便于单独测试）
# ===================================================================

def _ts_to_dt(value: Any) -> datetime:
    try:
        if isinstance(value, (int, float)) and value > 0:
            ts = float(value) / 1000 if value > 10_000_000_000 else float(value)
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
    except (ValueError, OSError):
        pass
    return datetime.utcnow()


def _normalize_author(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": user.get("userid") or user.get("id") or user.get("user_id") or "",
        "nickname": user.get("nickname") or user.get("name") or "",
        "avatar": user.get("image") or user.get("images") or user.get("avatar") or "",
        "fans_count": int(user.get("fans") or user.get("fans_count") or 0),
    }


def _normalize_stats(note: Dict[str, Any]) -> Dict[str, int]:
    return {
        "likes":    int(note.get("liked_count") or note.get("likes") or 0),
        "comments": int(note.get("comments_count") or note.get("comments") or 0),
        "shares":   int(note.get("shared_count") or note.get("shares") or 0),
        "collects": int(note.get("collected_count") or note.get("collects") or 0),
    }


def _extract_tags(note: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    for key in ("hash_tag", "topics", "tags"):
        for item in note.get(key) or []:
            if isinstance(item, dict):
                name = item.get("name") or item.get("title")
                if name:
                    tags.append(name)
            elif isinstance(item, str):
                tags.append(item)
    seen: set = set()
    return [t for t in tags if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]


def _extract_media(note: Dict[str, Any]) -> List[Dict[str, Any]]:
    media: List[Dict[str, Any]] = []
    for img in note.get("images_list") or []:
        url = img.get("url") or img.get("url_size_large") or img.get("original")
        if url:
            media.append({"type": "image", "url": url,
                          "width": img.get("width"), "height": img.get("height")})
    return media


def _norm_note(note: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """通用笔记归一化；user 可从外层传入（fetch_feed_notes_v2 格式）"""
    author_raw = user or note.get("user") or {}
    return {
        "note_id":      note.get("id") or note.get("note_id") or "",
        "title":        note.get("title") or "",
        "content":      note.get("desc") or note.get("content") or "",
        "type":         "video" if note.get("type") == "video" else "normal",
        "author":       _normalize_author(author_raw),
        "stats":        _normalize_stats(note),
        "published_at": _ts_to_dt(note.get("time") or note.get("timestamp")),
        "tags":         _extract_tags(note),
        "media":        _extract_media(note),
        "ip_location":  note.get("ip_location"),
        "xsec_token":   note.get("xsec_token"),
    }


def _norm_comment(raw: Dict[str, Any], note_id: str) -> Dict[str, Any]:
    sub_raw = raw.get("sub_comments") or []
    replies = [_norm_comment(s, note_id) for s in sub_raw]
    return {
        "comment_id": raw.get("id") or raw.get("comment_id") or "",
        "note_id":    raw.get("note_id") or note_id,
        "content":    raw.get("content") or "",
        "author":     _normalize_author(raw.get("user") or {}),
        "likes":      int(raw.get("like_count") or raw.get("likes") or 0),
        "created_at": _ts_to_dt(raw.get("time")),
        "replies":    replies,
        "sub_comment_cursor": raw.get("sub_comment_cursor") or "",
    }


# ===================================================================
# HTTP 层（带域名 failover）
# ===================================================================

class _Http:
    """aiohttp 封装 + dev→io failover"""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._domains = [settings.TIKHUB_BASE_URL, settings.TIKHUB_FALLBACK_BASE_URL]

    async def get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {settings.TIKHUB_TOKEN}"}
        clean = {k: v for k, v in params.items() if v is not None and v != ""}
        timeout = aiohttp.ClientTimeout(total=settings.TIKHUB_REQUEST_TIMEOUT_SECONDS)
        last_err: Optional[TikHubError] = None

        for domain in self._domains:
            url = f"{domain}{path}"
            try:
                async with self._session.get(url, params=clean,
                                             headers=headers, timeout=timeout) as resp:
                    body = await resp.json(content_type=None)

                    if resp.status in (401, 403):
                        raise TikHubFatalError(
                            f"认证失败 ({resp.status}): {url}"
                        )
                    if resp.status >= 400 or (isinstance(body, dict) and "detail" in body):
                        req_id = (body.get("detail") or {}).get("request_id", "") \
                                 if isinstance(body, dict) else ""
                        last_err = TikHubRetriableError(
                            f"HTTP {resp.status} {url} req_id={req_id}"
                        )
                        logger.warning("尝试 %s 失败，切换域名: %s", domain, last_err)
                        continue

                    return body if isinstance(body, dict) else {}

            except TikHubFatalError:
                raise
            except TikHubRetriableError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_err = TikHubRetriableError(f"网络异常 {url}: {e}")
                logger.warning("网络异常，切换域名: %s", last_err)
                continue

        raise last_err or TikHubRetriableError("所有域名均不可达")


# ===================================================================
# XHS 适配器（三个固定端点）
# ===================================================================

_SEARCH_PATH   = "/api/v1/xiaohongshu/app/search_notes"
_DETAIL_PATH   = "/api/v1/xiaohongshu/web_v2/fetch_feed_notes_v2"
_COMMENTS_PATH = "/api/v1/xiaohongshu/web_v2/fetch_note_comments"


class XHSAdapter:

    def __init__(self, http: _Http) -> None:
        self._http = http

    # ---- 搜索 ----
    async def search_notes(self, keyword: str, page: int = 1) -> List[Dict[str, Any]]:
        """
        app/search_notes → data.data.items[]
        endpoint 有"冷启动首次 400"已知问题，调用前由 TikHubClient 做一次重试。
        """
        resp = await self._http.get(_SEARCH_PATH, {"keyword": keyword, "page": page})
        outer = resp.get("data") or {}
        # app API 结构: resp.data.code/success/data.items
        inner = outer.get("data") if isinstance(outer, dict) else None
        if not isinstance(inner, dict):
            logger.debug("search_notes data 结构异常: %s", type(inner).__name__)
            return []
        items = inner.get("items") or inner.get("notes") or []
        results = []
        for item in items:
            note_raw = item.get("note") or item
            norm = _norm_note(note_raw)
            norm["search_keyword"] = keyword
            if norm["note_id"]:
                results.append(norm)
        return results

    # ---- 详情 ----
    async def get_note_detail(self, note_id: str) -> Dict[str, Any]:
        """
        web_v2/fetch_feed_notes_v2 → data.note_list[0]，用户在 data.user
        """
        resp = await self._http.get(_DETAIL_PATH, {"note_id": note_id})
        data = resp.get("data") or {}
        if not isinstance(data, dict):
            raise TikHubRetriableError(f"fetch_feed_notes_v2 data 异常: {type(data).__name__}")
        note_list = data.get("note_list") or []
        if not note_list:
            raise TikHubRetriableError(f"fetch_feed_notes_v2 note_list 为空, note_id={note_id}")
        note = note_list[0]
        # user 优先用外层（更完整），fallback note 内嵌
        user = data.get("user") or note.get("user") or {}
        return _norm_note(note, user=user)

    # ---- 评论 ----
    async def get_note_comments(
        self, note_id: str, cursor: str = ""
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        web_v2/fetch_note_comments → data.comments + data.cursor（JSON 字符串）
        """
        resp = await self._http.get(
            _COMMENTS_PATH, {"note_id": note_id, "cursor": cursor}
        )
        data = resp.get("data") or {}
        if not isinstance(data, dict):
            return [], ""
        raw_comments = data.get("comments") or []
        comments = [_norm_comment(c, note_id) for c in raw_comments]
        next_cursor = data.get("cursor") or ""
        # cursor 已是 JSON 字符串，直接透传
        return comments, str(next_cursor) if next_cursor else ""


# ===================================================================
# TikHubClient（门面，带 search 重试）
# ===================================================================

class TikHubClient:
    """业务接口；app/search_notes 首次 400 时自动重试一次"""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._adapter: Optional[XHSAdapter] = None

    async def _ensure_ready(self) -> XHSAdapter:
        if self._adapter is None:
            self._session = aiohttp.ClientSession()
            self._adapter = XHSAdapter(_Http(self._session))
        return self._adapter

    async def aclose(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._adapter = None

    async def search_notes(self, keyword: str, page: int = 1) -> List[Dict[str, Any]]:
        """app/search_notes 有冷启动 400 问题，最多重试 3 次，间隔递增"""
        adapter = await self._ensure_ready()
        for attempt in range(3):
            try:
                return await adapter.search_notes(keyword, page)
            except TikHubRetriableError as e:
                if attempt < 2:
                    wait = (attempt + 1) * 2  # 2s, 4s
                    logger.warning("search_notes 第%d次失败，%ds后重试: %s", attempt + 1, wait, e)
                    await asyncio.sleep(wait)
                else:
                    raise
        return []

    async def get_note_detail(self, note_id: str) -> Dict[str, Any]:
        adapter = await self._ensure_ready()
        return await adapter.get_note_detail(note_id)

    async def get_note_comments(
        self, note_id: str, cursor: str = ""
    ) -> Tuple[List[Dict[str, Any]], str]:
        adapter = await self._ensure_ready()
        return await adapter.get_note_comments(note_id, cursor)


# 模块级单例（懒初始化）
tikhub_client = TikHubClient()
