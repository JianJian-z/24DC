import os
import argparse
import logging
import json
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich import print as rprint

import rag_config as config
from src.data_processor import DataProcessor
from src.vector_store import VectorStore
from src.retriever import Retriever
from src.evaluator import Evaluator

# 创建必要的目录
os.makedirs(config.LOG_DIR, exist_ok=True)
os.makedirs(config.INDEX_DIR, exist_ok=True)
# os.makedirs(os.path.join(config.INDEX_DIR, "poetry_index"), exist_ok=True)
# os.makedirs(os.path.join(config.INDEX_DIR, "idiom_index"), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_DIR, 'main.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
console = Console()

def build_indices():
    """构建向量索引"""
    console.print("[bold green]开始构建向量索引...[/bold green]")
    vector_store = VectorStore()
    
    # 构建诗词索引
    console.print("[bold]处理诗词数据...[/bold]")
    vector_store.create_poetry_index()
    
    # 构建成语索引
    console.print("[bold]处理成语数据...[/bold]")
    vector_store.create_idiom_index()
    
    console.print("[bold green]索引构建完成！[/bold green]")

def query_rag_system(query_text: str, top_k: int = config.TOP_K, output_file: str = None):
    """查询RAG系统"""
    output_file=r'red.txt'
    # breakpoint()  # Python 3.7及以后推荐用法
    retriever = Retriever()
    recommendations = retriever.recommend_for_text(query_text, top_k=top_k)
    formatted_results = retriever.format_recommendations(recommendations)
    # with open(r'test_r.txt','r',encoding='utf8') as f:
    # 创建文件Console对象
    file_console = None
    if output_file:
        file_console = Console(file=open(output_file, "w", encoding="utf-8"), width=120)
    res_rec={"诗词":[],"成语":[]}
    # 打印格式化结果a
    for i, result in enumerate(formatted_results):
        
        console.print(f"[bold]原文片段 {i+1}:[/bold] {result['original_text']}")
        
        table = Table(title=f"推荐项 (片段 {i+1})")
        table.add_column("类型", style="cyan")
        table.add_column("内容", style="green")
        table.add_column("详情", style="yellow")
        table.add_column("相似度", style="red")
        
        for rec in result["recommendations"]:
            if rec["type"] == "poetry_line":
                table.add_row(
                    rec["type"], 
                    f"{rec['content']}",
                    f"{rec['source']}", 
                    rec["score"]
                )
                res_rec["诗词"].append(rec["content"])
            else:  # 成语
                table.add_row(
                    rec["type"], 
                    f"{rec['content']}",
                    f"{rec['source']}",
                    rec["score"]
                )
                res_rec["成语"].append(rec["content"])
        
        console.print(table)
        console.print("---" * 20)
        # 如果指定了输出文件，也写入文件
        if file_console:
            file_console.print(f"[bold]原文片段 {i+1}:[/bold] {result['original_text']}")
            file_console.print(table)
            file_console.print("---" * 20)
    
    # 关闭文件
    if output_file and file_console:
        file_console.file.close()
    res_rec["成语"]=list(set(res_rec["成语"]))
    res_rec["诗词"]=list(set(res_rec["诗词"]))
    # print(res_rec)
    
    # 如果需要更详细的内容：
    # return formatted_results
    
    return res_rec

def evaluate_system(test_cases: List[Dict[str, Any]]):
    """评估RAG系统"""
    retriever = Retriever()
    evaluator = Evaluator(retriever)
    
    metrics = evaluator.evaluate_recommendations(test_cases)
    
    console.print("[bold]评估结果:[/bold]")
    for metric, value in metrics.items():
        console.print(f"[cyan]{metric}:[/cyan] {value:.4f}")
    
    return metrics

def main():
    parser = argparse.ArgumentParser(description="古诗词成语RAG系统")
    parser.add_argument("--build", action="store_true", help="构建向量索引")
    parser.add_argument("--query", type=str, help="查询文本")
    parser.add_argument("--evaluate", action="store_true", help="评估系统性能")
    parser.add_argument("--test-file", type=str, help="测试文件路径")
    parser.add_argument("--top-k", type=int, default=config.TOP_K, help="返回结果数量")
    
    args = parser.parse_args()
    
    if args.build:
        build_indices()
    
    if args.query:
        query_rag_system(args.query, top_k=args.top_k)
    
    if args.evaluate:
        if args.test_file:
            with open(args.test_file, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)
            evaluate_system(test_cases)
        else:
            console.print("[bold red]评估需要提供测试文件路径 (--test-file)[/bold red]")

if __name__ == "__main__":
    main()