"""WebSocket 门面：重导出 __init__.py 里的实现"""
from src.websocket import WebSocketManager, websocket_manager

__all__ = ["WebSocketManager", "websocket_manager"]
