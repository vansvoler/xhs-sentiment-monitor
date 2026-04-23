"""
MongoDB 数据库连接管理
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from src.config import settings


class MongoDB:
    """MongoDB 连接管理类"""
    
    client: Optional[AsyncIOMotorClient] = None
    database = None
    
    async def connect(self):
        """连接MongoDB"""
        if self.client is None:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.database = self.client[settings.MONGODB_DB_NAME]
            print(f"已连接到MongoDB: {settings.MONGODB_URL}")
    
    async def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            print("MongoDB连接已关闭")
    
    def get_collection(self, collection_name: str):
        """获取集合"""
        if self.database is None:
            raise RuntimeError("MongoDB未初始化")
        return self.database[collection_name]


mongodb = MongoDB()


async def init_mongodb():
    """初始化MongoDB连接"""
    await mongodb.connect()


async def close_mongodb():
    """关闭MongoDB连接"""
    await mongodb.close()
