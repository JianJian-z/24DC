import os
from pathlib import Path
import torch
# 项目根目录
ROOT_DIR = Path(__file__).parent.absolute()

# 数据目录
DATA_DIR =r'datas'
POETRY_DATA_PATH = r'datas\result3.json'
IDIOM_DATA_PATH = r'datas\chengyu.json'

# 索引目录
INDEX_DIR = r'rag_recommand\index'
POETRY_INDEX_PATH = os.path.join(INDEX_DIR, "poetry_index")
IDIOM_INDEX_PATH = os.path.join(INDEX_DIR, "idiom_index")

# 日志目录
LOG_DIR =r'rag_recommand\logs'
# 模型配置
MODEL_NAME = "BAAI/bge-large-zh-v1.5"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 64
CHUNK_SIZE = 5000  # 处理大文件时的块大小

# 检索配置
TOP_K = 5  # 检索结果数量
SCORE_THRESHOLD = 0.5  # 检索相似度阈值

# 文本分块配置
# 分块参数调整
TEXT_CHUNK_SIZE = 300       # 从150增加到300，避免过小块
TEXT_CHUNK_OVERLAP = 30     # 从50减少到30，避免重叠过大
