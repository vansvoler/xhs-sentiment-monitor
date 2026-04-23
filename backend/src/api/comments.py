"""
评论 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from src.db.mongodb import mongodb
from src.models.comment import Comment

router = APIRouter()


@router.get("/", response_model=List[Comment])
async def list_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    note_id: Optional[str] = None
):
    """
    获取评论列表
    
    - skip: 跳过数量
    - limit: 返回数量
    - note_id: 笔记ID筛选
    """
    collection = mongodb.get_collection("comments")
    
    query = {}
    if note_id:
        query["note_id"] = note_id
    
    cursor = collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
    comments = await cursor.to_list(length=limit)
    
    return comments


@router.get("/{comment_id}", response_model=Comment)
async def get_comment(comment_id: str):
    """获取评论详情"""
    collection = mongodb.get_collection("comments")
    comment = await collection.find_one({"comment_id": comment_id})
    
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    return comment


@router.get("/note/{note_id}", response_model=List[Comment])
async def get_note_comments(
    note_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """获取指定笔记的评论"""
    collection = mongodb.get_collection("comments")
    
    cursor = collection.find({"note_id": note_id}).skip(skip).limit(limit).sort("likes", -1)
    comments = await cursor.to_list(length=limit)
    
    return comments
