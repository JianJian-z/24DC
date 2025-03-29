import os
import torch
import logging
import numpy as np
from typing import List, Dict, Any
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from faiss import IndexFlatIP, write_index, read_index
import pickle
import rag_config as rag_config
from src.data_processor import DataProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(rag_config.LOG_DIR, 'vector_store.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VectorStore:
    """向量存储类，用于处理文档嵌入和检索"""
    
    def __init__(self, model_name: str = rag_config.MODEL_NAME, device: str = rag_config.DEVICE):
        self.model = SentenceTransformer(model_name)
        self.model.to(device)
        self.device = device
    
    def create_poetry_index(self) -> None:
        """创建诗词向量索引"""
        logger.info("开始创建诗词向量索引...")
        
        # 确保索引目录存在
        os.makedirs(os.path.dirname(rag_config.INDEX_DIR), exist_ok=True)
        
        # 收集所有文档和元数据
        documents = []
        metadata = []
        
        # 流式处理诗词数据
        data_gen = DataProcessor.stream_json_data(rag_config.POETRY_DATA_PATH)
        chunk_gen = DataProcessor.chunk_data(data_gen, rag_config.CHUNK_SIZE)
        
        # 为索引创建目录
        index_dir = os.path.dirname(rag_config.POETRY_INDEX_PATH)
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        
        # 初始化索引
        first_chunk = True
        dimension = None
        
        for chunk in tqdm(chunk_gen, desc="处理诗词数据块"):
            # breakpoint()
            processed_chunk=[]
            texts=[]
            for item in chunk:
                processed_item=DataProcessor.process_poetry_data(item)
                processed_chunk.extend(processed_item)
            # processed_chunk = [DataProcessor.process_poetry_data(item) for item in chunk]
            # breakpoint()
            for item in processed_chunk:
                for_emb=item["text_for_embedding"]
                texts.append(for_emb)
            
            # 批量计算嵌入向量
            with torch.no_grad():
                embeddings = self.model.encode(texts, batch_size=rag_config.BATCH_SIZE, 
                                               show_progress_bar=True, convert_to_numpy=True)
            
            if first_chunk:
                dimension = embeddings.shape[1]
                index = IndexFlatIP(dimension)
                first_chunk = False
            
            # 添加向量到索引
            index.add(embeddings)
            
            # 保存元数据
            metadata.extend(processed_chunk)
        
        # 保存索引和元数据
        try:
            import pickle
            
            # 保存索引
            with open(f"{rag_config.POETRY_INDEX_PATH}.pkl", "wb") as f:
                pickle.dump(index, f)
            
            # 保存元数据
            torch.save(metadata, f"{rag_config.POETRY_INDEX_PATH}.meta")
            
            logger.info(f"诗词向量索引创建完成，共 {len(metadata)} 条记录")
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
            raise
    def create_idiom_index(self) -> None:
        """创建成语向量索引"""
        logger.info("开始创建成语向量索引...")
        
        # 确保索引目录存在
        os.makedirs(os.path.dirname(rag_config.IDIOM_INDEX_PATH), exist_ok=True)
        
        # 收集所有文档和元数据
        documents = []
        metadata = []
        
        # 流式处理成语数据
        data_gen = DataProcessor.stream_json_data(rag_config.IDIOM_DATA_PATH)
        chunk_gen = DataProcessor.chunk_data(data_gen, rag_config.CHUNK_SIZE)
        
        # 为索引创建目录
        index_dir = os.path.dirname(rag_config.IDIOM_INDEX_PATH)
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        
        # 初始化索引
        first_chunk = True
        dimension = None
        
        for chunk in tqdm(chunk_gen, desc="处理成语数据块"):
            # breakpoint()
            processed_chunk = [DataProcessor.process_idiom_data(item) for item in chunk]
            texts = [item["text_for_embedding"] for item in processed_chunk]
            
            # 批量计算嵌入向量
            with torch.no_grad():
                embeddings = self.model.encode(texts, batch_size=rag_config.BATCH_SIZE, 
                                               show_progress_bar=True, convert_to_numpy=True)
            
            if first_chunk:
                dimension = embeddings.shape[1]
                index = IndexFlatIP(dimension)
                first_chunk = False
            
            # 添加向量到索引
            index.add(embeddings)
            
            # 保存元数据
            metadata.extend(processed_chunk)
        try:
            
            
            # 保存索引
            with open(f"{rag_config.IDIOM_INDEX_PATH}.pkl", "wb") as f:
                pickle.dump(index, f)
            
            # 保存元数据
            torch.save(metadata, f"{rag_config.IDIOM_INDEX_PATH}.meta")
            
            logger.info(f"成语向量索引创建完成，共 {len(metadata)} 条记录")
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
            raise
        # # 保存索引和元数据
        # write_index(index, f"{config.IDIOM_INDEX_PATH}.faiss")
        # torch.save(metadata, f"{config.IDIOM_INDEX_PATH}.meta")
        
        # logger.info(f"成语向量索引创建完成，共 {len(metadata)} 条记录")
    
    def load_index(self, index_path: str):
        """加载向量索引"""
        try:
            index = read_index(f"{index_path}.faiss")
            metadata = torch.load(f"{index_path}.meta")
            return index, metadata
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            raise
        
    def load_index(self, index_path: str):
    
        try:
           
            # 加载索引
            with open(f"{index_path}.pkl", "rb") as f:
                index = pickle.load(f)
            
            # 加载元数据
            metadata = torch.load(f"{index_path}.meta")
            return index, metadata
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            raise
    