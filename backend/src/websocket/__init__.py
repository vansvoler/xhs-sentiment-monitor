"""
WebSocket 管理器
"""
from datetime import datetime
from fastapi import WebSocket
from typing import List, Set
import json
import asyncio
from src.config import settings


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscribers: Set[str] = set()
    
    async def connect(self, websocket: WebSocket):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        self.active_connections.remove(websocket)
        print(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        await websocket.send_text(message)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 移除失效连接
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_sentiment_update(self, sentiment_data: dict):
        """发送情感更新"""
        await self.broadcast({
            "type": "sentiment_update",
            "data": sentiment_data
        })
    
    async def send_new_note(self, note_data: dict):
        """发送新笔记通知"""
        await self.broadcast({
            "type": "new_note",
            "data": note_data
        })
    
    async def send_alert(self, alert_data: dict):
        """发送告警"""
        await self.broadcast({
            "type": "alert",
            "data": alert_data
        })
    
    async def heartbeat(self):
        """心跳检测"""
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            if self.active_connections:
                await self.broadcast({
                    "type": "heartbeat",
                    "timestamp": datetime.now()
                })
    
    async def disconnect_all(self):
        """断开所有连接"""
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except Exception:
                pass
        self.active_connections.clear()


websocket_manager = WebSocketManager()
