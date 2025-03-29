import os
import logging
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from faiss import IndexFlatIP

import rag_config as rag_config
from src.vector_store import VectorStore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(rag_config.LOG_DIR, 'retriever.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TextChunker:
    """文本分块器"""
    
    @staticmethod
    def split_text(text: str, chunk_size: int = rag_config.TEXT_CHUNK_SIZE, 
                overlap: int = rag_config.TEXT_CHUNK_OVERLAP) -> List[str]:
        """将文本分成重叠的块"""
        # 参数检查和安全处理
        if text is None:
            return []
        
        if not isinstance(text, str):
            text = str(text)
            
        # 空文本或小于块大小的文本直接返回
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        # 确保overlap小于chunk_size
        overlap = min(overlap, chunk_size - 1)
        if overlap < 0:
            overlap = 0
        
        chunks = []
        start = 0
        
        # 添加安全措施防止无限循环
        max_iterations = len(text) * 2  # 安全上限
        iteration = 0
        
        while start < len(text) and iteration < max_iterations:
            iteration += 1
            
            # 计算当前块的结束位置
            end = min(start + chunk_size, len(text))
            
            # 如果不是最后一个块且不在句子边界，尝试找到最近的句子边界
            if end < len(text):
                # 在当前块中查找最后一个分隔符
                punct_pos = -1
                for punct in ['。', '！', '？', '；', '\n', '.', '!', '?', ';']:
                    pos = text.rfind(punct, start, end)
                    if pos > punct_pos:  # 找到更靠后的标点符号
                        punct_pos = pos
                
                # 如果找到合适的分隔位置，调整块的结束位置
                if punct_pos != -1:
                    end = punct_pos + 1
            
            # 确保start和end在有效范围内
            if start >= len(text) or end <= start:
                break
                
            # 添加当前块到结果列表
            chunks.append(text[start:end])
            if end>=len(text)-1:
                break
            # 更新start位置，考虑重叠
            start = end - overlap
            
            # 防止无进展
            if start == end:
                start += 1
        
        return chunks


class Retriever:
    """检索器，用于查询相关的诗词或成语"""
    
    def __init__(self, model_name: str = rag_config.MODEL_NAME, device: str = rag_config.DEVICE):
        self.model = SentenceTransformer(model_name)
        self.model.to(device)
        self.device = device
        
        # 加载索引
        vector_store = VectorStore(model_name, device)
        self.poetry_index, self.poetry_metadata = vector_store.load_index(rag_config.POETRY_INDEX_PATH)
        self.idiom_index, self.idiom_metadata = vector_store.load_index(rag_config.IDIOM_INDEX_PATH)
    
    def retrieve(self, query: str, top_k: int = rag_config.TOP_K, 
                score_threshold: float = rag_config.SCORE_THRESHOLD) -> List[Dict[str, Any]]:
        """检索与查询相关的诗词和成语"""
        # 查询向量化
        query_vector = self.model.encode([query], convert_to_numpy=True)
        
        # 检索诗词
        poetry_scores, poetry_indices = self.poetry_index.search(query_vector, top_k)
        poetry_results = [
            {**self.poetry_metadata[idx], "score": float(score)}
            for score, idx in zip(poetry_scores[0], poetry_indices[0])
            if score >= score_threshold
        ]
        
        # 检索成语
        idiom_scores, idiom_indices = self.idiom_index.search(query_vector, top_k)
        idiom_results = [
            {**self.idiom_metadata[idx], "score": float(score)}
            for score, idx in zip(idiom_scores[0], idiom_indices[0])
            if score >= score_threshold
        ]
        
        # 合并结果并按相似度排序
        all_results = poetry_results + idiom_results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        return all_results[:top_k]
    
    def recommend_for_text(self, text: str, top_k: int = rag_config.TOP_K) -> List[Dict[str, Any]]:
        """为长文本提供诗词和成语推荐"""
        # 将文本分块
        chunks = TextChunker.split_text(text)
        
        all_recommendations = []
        
        # 为每个块检索相关内容
        for chunk in chunks:
            chunk_results = self.retrieve(chunk, top_k)
            if chunk_results:
                all_recommendations.append({
                    "chunk": chunk,
                    "recommendations": chunk_results
                })
        
        return all_recommendations
    
    def format_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化推荐结果，便于展示"""
        formatted_results = []
        
        for rec in recommendations:
            chunk = rec["chunk"]
            chunk_recs = []
            
            for item in rec["recommendations"]:
                if item["type"] == "poetry_line":
                    formatted = {
                        "type":"poetry_line",
                        "content": item["line"],  # 单句内容
                        "source": f"{item['title']} **** {item['dynasty']} **** {item['author']}",
                        "score": f"{item['score']:.4f}"
                    }
                else:  # idiom
                    formatted = {
                        "type":"idiom",
                        "content": item["idiom"],
                        "source": f"成语 **** {item['explanation']}**** {item['usage']}",
                        "score": f"{item['score']:.4f}"
                        
                        # "type": "成语",
                        
                        # "idiom": item["idiom"],
                        # "explanation": item["explanation"],
                        # "usage": item["usage"],
                        # "score": f"{item['score']:.4f}"
                    }
                chunk_recs.append(formatted)
            
            formatted_results.append({
                "original_text": chunk,
                "recommendations": chunk_recs
            })
        
        return formatted_results