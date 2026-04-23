"""
竞品监控服务
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from src.db.mongodb import mongodb
from src.models.note import CompetitorData, SentimentLabel
from src.config import settings


class CompetitorMonitor:
    """竞品监控器"""
    
    async def analyze_competitor(self, name: str, days: int = 30) -> CompetitorData:
        """
        分析竞品
        
        Args:
            name: 竞品名称
            days: 分析天数
            
        Returns:
            竞品数据
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        
        notes_collection = mongodb.get_collection("notes")
        notes_cursor = notes_collection.find({
            "category": name,
            "collected_at": {"$gte": start_time}
        })
        
        notes = await notes_cursor.to_list(length=None)
        
        note_count = len(notes)
        
        if note_count == 0:
            return CompetitorData(
                name=name,
                note_count=0,
                avg_sentiment_score=0.5,
                positive_rate=0.0,
                negative_rate=0.0,
                total_mentions=0
            )
        
        # 统计情感分布
        positive_count = sum(1 for n in notes 
                            if n.get("sentiment", {}).get("label") == SentimentLabel.POSITIVE.value)
        negative_count = sum(1 for n in notes 
                            if n.get("sentiment", {}).get("label") == SentimentLabel.NEGATIVE.value)
        
        positive_rate = positive_count / note_count if note_count > 0 else 0
        negative_rate = negative_count / note_count if note_count > 0 else 0
        
        # 计算平均情感得分
        sentiment_scores = [
            n.get("sentiment", {}).get("score", 0.5)
            for n in notes
            if n.get("sentiment")
        ]
        avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5
        
        # 统计总提及次数（评论数）
        total_mentions = sum(
            n.get("stats", {}).get("comments", 0)
            for n in notes
        )
        
        return CompetitorData(
            name=name,
            note_count=note_count,
            avg_sentiment_score=avg_score,
            positive_rate=positive_rate,
            negative_rate=negative_rate,
            total_mentions=total_mentions
        )
    
    async def compare_competitors(
        self,
        names: List[str] = None,
        days: int = 30
    ) -> List[CompetitorData]:
        """
        比较多个竞品
        
        Args:
            names: 竞品名称列表，默认使用配置中的竞品列表
            days: 分析天数
            
        Returns:
            竞品数据列表
        """
        if names is None:
            names = settings.COMPETITORS
        
        results = []
        for name in names:
            data = await self.analyze_competitor(name, days)
            results.append(data)
        
        return sorted(results, key=lambda x: x.note_count, reverse=True)
    
    async def get_competitor_trends(
        self,
        name: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取竞品趋势
        
        Args:
            name: 竞品名称
            days: 分析天数
            
        Returns:
            趋势数据列表
        """
        trends = []
        
        for i in range(days):
            day = datetime.utcnow() - timedelta(days=i)
            start_time = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            notes_collection = mongodb.get_collection("notes")
            notes_cursor = notes_collection.find({
                "category": name,
                "collected_at": {"$gte": start_time, "$lt": end_time}
            })
            
            notes = await notes_cursor.to_list(length=None)
            
            positive_count = sum(1 for n in notes 
                                if n.get("sentiment", {}).get("label") == SentimentLabel.POSITIVE.value)
            negative_count = sum(1 for n in notes 
                                if n.get("sentiment", {}).get("label") == SentimentLabel.NEGATIVE.value)
            
            trends.append({
                "date": start_time,
                "note_count": len(notes),
                "positive_count": positive_count,
                "negative_count": negative_count
            })
        
        return trends[::-1]


competitor_monitor = CompetitorMonitor()
