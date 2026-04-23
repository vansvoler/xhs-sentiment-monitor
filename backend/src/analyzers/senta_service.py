"""
情感分析服务 - 百度Senta集成
"""
from typing import List
import time
from src.models.note import SentimentResult, SentimentLabel, EmotionType
from src.config import settings  # noqa: F401


class SentaService:
    """百度Senta情感分析服务"""
    
    def __init__(self):
        self.model = None
        self.use_cuda = True
    
    def init_model(self):
        """初始化模型"""
        try:
            from senta import Senta
            self.model = Senta()
            # 使用ERNIE模型进行中文情感分类
            self.model.init_model(
                model_class="ernie_1.0_skep_large_ch",
                task="sentiment_classify",
                use_cuda=self.use_cuda
            )
            print("百度Senta模型初始化成功")
        except ImportError:
            print("警告: senta库未安装，使用简单规则")
            self.model = None
        except Exception as e:
            print(f"模型初始化失败: {e}")
            self.model = None
    
    def analyze(self, text: str) -> SentimentResult:
        """
        分析单条文本情感
        
        Args:
            text: 待分析文本
            
        Returns:
            情感分析结果
        """
        if self.model is None:
            return self._rule_based_analysis(text)
        
        try:
            result = self.model.predict([text])[0]
            
            # 将Senta结果转换为标准格式
            label = self._convert_label(result)
            score = result.get("confidence", 0.5)
            emotion = self._infer_emotion(text, label)
            
            return SentimentResult(
                label=label,
                score=score,
                emotion=emotion
            )
        except Exception as e:
            print(f"情感分析失败: {e}")
            return self._rule_based_analysis(text)
    
    def batch_analyze(self, texts: List[str]) -> List[SentimentResult]:
        """
        批量分析文本情感
        
        Args:
            texts: 待分析文本列表
            
        Returns:
            情感分析结果列表
        """
        results = []
        
        if self.model is not None:
            try:
                batch_results = self.model.predict(texts)
                for text, result in zip(texts, batch_results):
                    label = self._convert_label(result)
                    score = result.get("confidence", 0.5)
                    emotion = self._infer_emotion(text, label)
                    results.append(SentimentResult(
                        label=label,
                        score=score,
                        emotion=emotion
                    ))
                return results
            except Exception as e:
                print(f"批量情感分析失败: {e}")
        
        # 回退到规则分析
        for text in texts:
            results.append(self._rule_based_analysis(text))
        
        return results
    
    def _rule_based_analysis(self, text: str) -> SentimentResult:
        """
        基于规则的情感分析（备用方案）
        
        Args:
            text: 待分析文本
            
        Returns:
            情感分析结果
        """
        positive_words = ["好", "棒", "不错", "喜欢", "推荐", "爱", "满意", "优秀", "完美"]
        negative_words = ["差", "不好", "讨厌", "失望", "垃圾", "烂", "糟糕", "糟糕", "后悔"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            label = SentimentLabel.POSITIVE
            score = 0.7
            emotion = EmotionType.JOY
        elif negative_count > positive_count:
            label = SentimentLabel.NEGATIVE
            score = 0.7
            emotion = EmotionType.ANGER
        else:
            label = SentimentLabel.NEUTRAL
            score = 0.5
            emotion = EmotionType.NEUTRAL
        
        return SentimentResult(
            label=label,
            score=score,
            emotion=emotion
        )
    
    def _convert_label(self, result: dict) -> SentimentLabel:
        """转换情感标签"""
        label = result.get("label", 0)
        if label == 1:
            return SentimentLabel.POSITIVE
        elif label == 2:
            return SentimentLabel.NEGATIVE
        else:
            return SentimentLabel.NEUTRAL
    
    def _infer_emotion(self, text: str, label: SentimentLabel) -> EmotionType:
        """推断情绪类型"""
        emotion_keywords = {
            EmotionType.JOY: ["开心", "高兴", "喜欢", "爱", "满足", "满意"],
            EmotionType.ANGER: ["生气", "愤怒", "讨厌", "恨", "恶心"],
            EmotionType.SADNESS: ["难过", "伤心", "痛苦", "遗憾", "失望"],
            EmotionType.FEAR: ["害怕", "恐惧", "担心", "焦虑"],
            EmotionType.SURPRISE: ["惊讶", "意外", "没想到", "震惊"]
        }
        
        if label == SentimentLabel.NEUTRAL:
            return EmotionType.NEUTRAL
        
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return emotion
        
        return EmotionType.JOY if label == SentimentLabel.POSITIVE else EmotionType.ANGER


    def _rule_based_analysis_batch(self, texts: list) -> list:
        """批量规则分析（供 LLM 降级用）"""
        return [self._rule_based_analysis(t) for t in texts]


senta_service = SentaService()


def init_sentiment_service():
    """初始化情感分析服务"""
    senta_service.init_model()


def get_sentiment_service():
    """
    工厂函数：根据 SENTIMENT_PROVIDER 返回对应服务。
      llm   → LLMSentimentService（MiniMax / GLM / 任意 OpenAI 兼容）
      senta → SentaService（ERNIE 模型，需安装 senta + PaddlePaddle）
      rule  → SentaService（纯规则，零依赖）
    """
    from src.config import settings

    provider = (settings.SENTIMENT_PROVIDER or "rule").lower()

    if provider == "llm":
        from src.analyzers.llm_sentiment import LLMSentimentService
        return LLMSentimentService()

    # senta / rule：都走 SentaService，init_model 决定是否加载模型
    if provider == "senta":
        senta_service.init_model()
    return senta_service
