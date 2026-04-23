"""
趋势分析服务
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
from src.db.mongodb import mongodb
from src.models.note import TrendData, SentimentLabel


class TrendAnalyzer:
    """趋势分析器"""
    
    async def analyze_daily_trend(self, date: datetime = None) -> TrendData:
        """
        分析日趋势
        
        Args:
            date: 分析日期，默认为今天
            
        Returns:
            趋势数据
        """
        if date is None:
            date = datetime.utcnow()
        
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        # 获取当天的笔记
        notes_collection = mongodb.get_collection("notes")
        notes_cursor = notes_collection.find({
            "collected_at": {"$gte": start_time, "$lt": end_time}
        })
        
        notes = await notes_cursor.to_list(length=None)
        
        # 获取当天的评论
        comments_collection = mongodb.get_collection("comments")
        comments_cursor = comments_collection.find({
            "collected_at": {"$gte": start_time, "$lt": end_time}
        })
        
        comments = await comments_cursor.to_list(length=None)
        
        # 统计情感分布
        positive_count = sum(1 for n in notes 
                            if n.get("sentiment", {}).get("label") == SentimentLabel.POSITIVE.value)
        negative_count = sum(1 for n in notes 
                            if n.get("sentiment", {}).get("label") == SentimentLabel.NEGATIVE.value)
        neutral_count = sum(1 for n in notes 
                           if n.get("sentiment", {}).get("label") == SentimentLabel.NEUTRAL.value)
        
        # 计算平均情感得分
        sentiment_scores = [
            n.get("sentiment", {}).get("score", 0.5)
            for n in notes
            if n.get("sentiment")
        ]
        avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5
        
        # 提取热词
        keywords = []
        for note in notes:
            keywords.extend(note.get("keywords", []))
        hot_keywords = [k for k, _ in Counter(keywords).most_common(10)]
        
        return TrendData(
            timestamp=start_time,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            total_notes=len(notes),
            total_comments=len(comments),
            avg_sentiment_score=avg_score,
            hot_keywords=hot_keywords
        )
    
    async def get_trend_series(
        self,
        days: int = 7
    ) -> List[TrendData]:
        """
        获取趋势序列
        
        Args:
            days: 天数
            
        Returns:
            趋势数据列表
        """
        trends = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            trend = await self.analyze_daily_trend(date)
            trends.append(trend)
        
        return trends[::-1]  # 按时间正序返回
    
    async def get_hot_topics(
        self,
        limit: int = 10,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        获取热门话题
        
        Args:
            limit: 返回数量
            hours: 时间窗口（小时）
            
        Returns:
            热门话题列表
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        notes_collection = mongodb.get_collection("notes")
        notes_cursor = notes_collection.find({
            "collected_at": {"$gte": start_time}
        }).sort([("stats.likes", -1), ("stats.comments", -1)])
        
        notes = await notes_cursor.to_list(length=limit)
        
        topics = []
        for note in notes:
            topics.append({
                "note_id": note.get("note_id"),
                "title": note.get("title"),
                "tags": note.get("tags", []),
                "likes": note.get("stats", {}).get("likes", 0),
                "comments": note.get("stats", {}).get("comments", 0),
                "sentiment": note.get("sentiment")
            })
        
        return topics


trend_analyzer = TrendAnalyzer()
