"""
小红书舆情监控系统 - 主入口
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.config import settings
from src.db.mongodb import init_mongodb, close_mongodb
from src.websocket.manager import websocket_manager
from src.api import notes, comments, sentiment, trends, competitors, config
from src.collectors.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    print("启动系统...")

    # 初始化数据库连接
    await init_mongodb()

    # 启动任务调度器
    start_scheduler()

    # 启动 WebSocket 心跳
    asyncio.create_task(websocket_manager.heartbeat())

    print("系统启动完成")

    yield
    
    # 清理资源
    print("关闭系统...")
    stop_scheduler()
    await close_mongodb()
    await websocket_manager.disconnect_all()
    print("系统已关闭")


app = FastAPI(
    title="小红书舆情监控系统",
    description="实时监控小红书笔记和评论的情感倾向",
    version="0.1.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(notes.router, prefix="/api/notes", tags=["笔记"])
app.include_router(comments.router, prefix="/api/comments", tags=["评论"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["情感分析"])
app.include_router(trends.router, prefix="/api/trends", tags=["趋势分析"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["竞品分析"])
app.include_router(config.router, prefix="/api/config", tags=["配置"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "小红书舆情监控系统API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时推送端点"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # 保持连接，忽略客户端上行消息
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
