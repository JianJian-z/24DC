import json
import os
import logging
from typing import List, Dict, Any, Generator
from tqdm import tqdm
import re
import rag_config as rag_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(rag_config.LOG_DIR, 'data_processor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataProcessor:
    """大规模JSON数据处理类"""
    
    @staticmethod
    def stream_json_data(file_path: str) -> Generator[Dict[str, Any], None, None]:
        """流式读取大型JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 检查文件是否以[开头(列表)
                first_char = f.read(1)
                f.seek(0)
                
                if first_char == '[':
                    # 如果是JSON数组，使用ijson流式解析
                    import ijson
                    yield from ijson.items(f, 'item')
                else:
                    # 如果是每行一个JSON对象
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON line: {line[:100]}...")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def process_poetry_data(data_item: Dict[str, Any]) -> Dict[str, Any]:
        """处理诗词数据项"""
        # processed_item = {
        #     "id": hash(str(data_item)),  # 生成唯一ID
        #     "type": "poetry",
        #     "title": data_item.get("古诗名", ""),
        #     "author": data_item.get("作者", ""),
        #     "dynasty": data_item.get("朝代", ""),
        #     "content": '\n'.join(data_item.get("内容", [])) if isinstance(data_item.get("内容"), list) else data_item.get("内容", ""),
        #     "appreciation": data_item.get("注释", ""),
        #     "category": data_item.get("类型", []),
        #     "text_for_embedding": ""  # 将在下面填充
        # }
        
        # # 构建用于嵌入的文本
        # content_text = processed_item["content"]
        # title_text = processed_item["title"]
        # processed_item["text_for_embedding"] = f"{title_text} {content_text}"
        
        # return processed_item
        poetry_lines = []
        content_lines = data_item.get("内容", [])
        
        if isinstance(content_lines, str):
            # 将整首诗拆分成单句
            lines = [line for line in re.split(r'[，。、？！]', content_lines) if line.strip()]
        else:
            lines = []
            for line in content_lines:
                # 去除标点符号
                clean_line = re.sub(r'[，。、？！]', '', line)
                # 如果非空，添加到结果列表
                if clean_line.strip():
                    lines.append(clean_line)
                    
        # 为每句创建索引项，保留诗的元数据
        for i, line in enumerate(lines):
            line_item = {
                "id": f"{hash(str(data_item))}-{i}",  # 生成唯一ID
                "type": "poetry_line",
                "line": line,                        # 单句内容
                "line_index": i,                     # 句子在原诗中的位置
                "title": data_item.get("古诗名", ""),  # 保留原诗标题
                "author": data_item.get("作者", ""),   # 保留作者
                "dynasty": data_item.get("朝代", ""),  # 保留朝代
                "full_content": '\n'.join(content_lines) if isinstance(content_lines, list) else content_lines,
                "text_for_embedding": line           # 以单句作为向量化对象
            }
            poetry_lines.append(line_item)
        
        return poetry_lines
    
    @staticmethod
    def process_idiom_data(data_item: Dict[str, Any]) -> Dict[str, Any]:
        """处理成语数据项"""
        processed_item = {
            "id": hash(str(data_item)),  # 生成唯一ID
            "type": "idiom",
            "idiom": data_item.get("成语", ""),
            "pinyin": data_item.get("拼音", ""),
            "explanation": data_item.get("解释", ""),
            "source": data_item.get("出处", ""),
            "example": data_item.get("例子", ""),
            "usage": data_item.get("用法", ""),
            "emotion": data_item.get("感情", ""),
            "synonyms": data_item.get("近义", ""),
            "antonyms": data_item.get("反义", ""),
            "text_for_embedding": ""  # 将在下面填充
        }
        
        # 构建用于嵌入的文本
        idiom_text = processed_item["idiom"]
        explanation_text = processed_item["explanation"]
        usage_text = processed_item["usage"]
        processed_item["text_for_embedding"] = f"{idiom_text} {explanation_text}"
        
        return processed_item
    
    @staticmethod
    def chunk_data(data_generator: Generator[Dict[str, Any], None, None], 
                  chunk_size: int) -> Generator[List[Dict[str, Any]], None, None]:
        """将数据分块处理，适用于大数据集"""
        chunk = []
        for item in data_generator:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:  # 不要忘记最后一个不完整的块
            yield chunk