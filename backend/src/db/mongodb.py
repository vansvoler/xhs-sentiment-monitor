"""
MongoDB 异步客户端
"""

import logging
from typing import Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from src.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB 连接单例"""

    def __init__(self) -> None:
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """建立连接并创建索引"""
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        await self._ensure_indexes()
        logger.info(
            "MongoDB 连接成功: %s/%s", settings.MONGODB_URL, settings.MONGODB_DB_NAME
        )

    async def _ensure_indexes(self) -> None:
        """建立查询/唯一索引"""
        assert self.db is not None
        notes = self.db["notes"]
        comments = self.db["comments"]

        # notes 唯一 + 常用排序字段
        await notes.create_index("note_id", unique=True)
        await notes.create_index("dedup_key")  # (作者+发布时间) 规范去重键
        await notes.create_index("collected_at")
        await notes.create_index("published_at")  # 列表/趋势的时间轴排序
        await notes.create_index("comments_collected_at")
        await notes.create_index([("sentiment.label", 1), ("collected_at", -1)])
        await notes.create_index("category")
        await notes.create_index([("category", 1), ("collected_at", -1)])
        # 负面工作台：影响力排序（粉丝数）
        await notes.create_index(
            [("sentiment.label", 1), ("author.fans_count", -1)]
        )

        # comments 唯一 + 关联笔记
        await comments.create_index("comment_id", unique=True)
        await comments.create_index("note_id")
        await comments.create_index("collected_at")
        # 负面工作台：影响力排序（点赞）
        await comments.create_index([("sentiment.label", 1), ("likes", -1)])

        # alerts 舆情预警
        alerts = self.db["alerts"]
        await alerts.create_index("alert_id", unique=True)
        await alerts.create_index([("status", 1), ("created_at", -1)])
        await alerts.create_index([("level", 1), ("created_at", -1)])

        # kol_profiles KOL 人工态 + 富化缓存
        kol_profiles = self.db["kol_profiles"]
        await kol_profiles.create_index("user_id", unique=True)
        await kol_profiles.create_index("enriched_at")

        # monitor_keywords 监控关键词（运行时可增删）
        monitor_keywords = self.db["monitor_keywords"]
        await monitor_keywords.create_index("keyword", unique=True)

    async def disconnect(self) -> None:
        """关闭连接"""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB 连接已关闭")

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """获取集合句柄"""
        if self.db is None:
            raise RuntimeError("MongoDB 未初始化，请先调用 init_mongodb()")
        return self.db[name]


mongodb = MongoDB()


async def init_mongodb() -> None:
    await mongodb.connect()


async def close_mongodb() -> None:
    await mongodb.disconnect()
