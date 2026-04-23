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
        logger.info("MongoDB 连接成功: %s/%s", settings.MONGODB_URL, settings.MONGODB_DB_NAME)

    async def _ensure_indexes(self) -> None:
        """建立查询/唯一索引"""
        assert self.db is not None
        notes = self.db["notes"]
        comments = self.db["comments"]

        # notes 唯一 + 常用排序字段
        await notes.create_index("note_id", unique=True)
        await notes.create_index("collected_at")
        await notes.create_index("comments_collected_at")
        await notes.create_index([("sentiment.label", 1), ("collected_at", -1)])
        await notes.create_index("category")
        await notes.create_index([("category", 1), ("collected_at", -1)])

        # comments 唯一 + 关联笔记
        await comments.create_index("comment_id", unique=True)
        await comments.create_index("note_id")
        await comments.create_index("collected_at")

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
