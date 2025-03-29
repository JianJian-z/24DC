import os
import logging
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

import rag_config as rag_config
from src.retriever import Retriever

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(rag_config.LOG_DIR, 'evaluator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Evaluator:
    """评估RAG系统的性能"""
    
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.model = retriever.model
    
    def calculate_semantic_relevance(self, text: str, recommendations: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算推荐的语义相关性"""
        if not recommendations:
            return {"avg_similarity": 0.0, "max_similarity": 0.0, "min_similarity": 0.0}
        
        # 获取原始文本的嵌入向量
        text_embedding = self.model.encode([text], convert_to_numpy=True)
        
        # 收集所有推荐项的嵌入向量
        rec_texts = []
        for rec in recommendations:
            for item in rec["recommendations"]:
                if item["type"] == "诗词":
                    rec_texts.append(item["content"])
                else:  # idiom
                    rec_texts.append(f"{item['idiom']} {item['explanation']}")
        
        if not rec_texts:
            return {"avg_similarity": 0.0, "max_similarity": 0.0, "min_similarity": 0.0}
        
        # 计算推荐项的嵌入向量
        rec_embeddings = self.model.encode(rec_texts, convert_to_numpy=True)
        
        # 计算相似度
        similarities = cosine_similarity(text_embedding, rec_embeddings)[0]
        
        return {
            "avg_similarity": float(np.mean(similarities)),
            "max_similarity": float(np.max(similarities)),
            "min_similarity": float(np.min(similarities))
        }
    
    def evaluate_recommendations(self, test_cases: List[Dict[str, Any]]) -> Dict[str, float]:
        """评估一组测试案例的推荐质量"""
        metrics = {
            "avg_similarity": [],
            "poetry_ratio": [],
            "idiom_ratio": [],
            "recommendation_count": []
        }
        
        for case in test_cases:
            text = case["text"]
            recommendations = self.retriever.recommend_for_text(text)
            formatted_recs = self.retriever.format_recommendations(recommendations)
            
            # 计算语义相关性
            relevance = self.calculate_semantic_relevance(text, recommendations)
            metrics["avg_similarity"].append(relevance["avg_similarity"])
            
            # 统计诗词和成语的比例
            poetry_count = 0
            idiom_count = 0
            total_recs = 0
            
            for rec in formatted_recs:
                for item in rec["recommendations"]:
                    total_recs += 1
                    if item["type"] == "诗词":
                        poetry_count += 1
                    else:
                        idiom_count += 1
            
            if total_recs > 0:
                metrics["poetry_ratio"].append(poetry_count / total_recs)
                metrics["idiom_ratio"].append(idiom_count / total_recs)
            metrics["recommendation_count"].append(total_recs)
        
        # 计算平均指标
        return {
            "avg_semantic_relevance": np.mean(metrics["avg_similarity"]).item(),
            "avg_poetry_ratio": np.mean(metrics["poetry_ratio"]).item() if metrics["poetry_ratio"] else 0,
            "avg_idiom_ratio": np.mean(metrics["idiom_ratio"]).item() if metrics["idiom_ratio"] else 0,
            "avg_rec_count": np.mean(metrics["recommendation_count"]).item()
        }