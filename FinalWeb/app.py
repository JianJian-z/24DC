'''
author       : 渐渐
Date         : 2025-03-31 14:19:08
LastEditTime : 2025-04-03 16:09:22
'''
from flask import Flask, render_template, request, redirect, url_for, jsonify 

import warnings
import time
import requests
from dotenv import load_dotenv
import os
import json
from search.elastic import Esearch

import subprocess
import time
import shlex  # 处理命令拆分（Unix-like 系统需要）

def start_elasticsearch():
    try:
        # 根据系统选择命令
        command = "elasticsearch"  # 通用命令（依赖 PATH 环境变量）

        # 启动进程（关键：shell=True 让系统解析 PATH）
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,            # 依赖 shell 解析 PATH 环境变量
            text=True
        )

        print("正在启动 Elasticsearch...")
        # 实时读取输出并检测启动成功标志
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                if "started" in output.lower():
                    print("✅ Elasticsearch 启动成功！")
                    break
        return process

    except FileNotFoundError:
        print("错误：找不到 'elasticsearch' 命令。请确保：")
        print("1. Elasticsearch 的 bin 目录已添加到系统 PATH 环境变量")
        print("2. 重启终端或IDE使环境变量生效")
    except Exception as e:
        print(f"启动失败: {str(e)}")


app = Flask(__name__, template_folder='template', static_folder='static')

# 忽略 Elasticsearch 警告

INDEX_NAME = "poetry_index"
# 配置Elasticsearch连接
es = Esearch(host="http://localhost:9200",
             index_name=INDEX_NAME)

# Elasticsearch(
#     "http://localhost:9200",
#     timeout=30,
#     max_retries=10,
#     retry_on_timeout=True
# )
es.create_index()  

@app.route('/')
def home():
    """首页"""
    return render_template('index.html')

@app.route('/traditional-trace')
def traditional_trace():
    return render_template('TraditionalTrace.html')

@app.route('/llm-trace')
def llm_trace():
    return render_template('LLMTrace.html')


load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


@app.route('/api/deepseek', methods=['POST'])
def deepseek_query():
    try:
        # 验证输入
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Missing 'question' field"}), 400
        
        # 构造文学检测专用提示词
        detection_prompt = f"""请严格分析以下文本中的古诗/成语化用情况：
        
        文本内容：{data['question']}

        要求：
        1. 识别直接引用或化用的中国古诗、成语
        2. 对每个发现提供：
            - 类型（poem/idiom）
            - 出处（如《唐诗三百首》）
            - 原文
            - 匹配文本片段
            - 相似度（0-100）
        3. 按JSON格式返回结果

        示例格式：
        {{
            "findings": [
            {{
                "type": "poem",
                "source": "李白《静夜思》",
                "original_text": "床前明月光",
                "matched_text": "窗前明月",
                "similarity": 90
            }}
            ],
            "analysis": "文本中检测到2处古诗化用"
        }}"""

        # 构造 DeepSeek 请求
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{
                "role": "user", 
                "content": detection_prompt
            }],
            "temperature": 0.3,  # 降低随机性提高准确性
            "response_format": { "type": "json_object" }
        }

        # 调用 API（带超时和重试）
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(3.05, 60)
        )
        response.raise_for_status()  # 自动处理 4XX/5XX 错误
        
        # 解析响应
        result = response.json()
        content = result['choices'][0]['message']['content']

        try:
            # 尝试解析返回的JSON
            findings_data = json.loads(content)
            return jsonify({
                "analysis": findings_data.get("analysis", ""),
                "findings": findings_data.get("findings", []),
                "usage": result.get('usage', {})
            })
        except json.JSONDecodeError:
            # 如果返回的不是标准JSON，返回原始内容
            return jsonify({
                "answer": content,
                "findings": [],
                "usage": result.get('usage', {})
            })

    except requests.exceptions.Timeout:
        return jsonify({"error": "API 响应超时"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API 请求失败: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@app.route('/search-results.html', methods=['GET'])
def search_results():
    """处理搜索请求"""
    query = request.args.get('s', '').strip()  # 使用's'获取搜索参数
    
    if not query:
        return redirect(url_for('home'))
    
    # 执行搜索
    start_time = time.time()
    results = perform_search(query)
    spend_time = round(time.time() - start_time, 2)
    
    # 准备模板变量
    template_vars = {
        'query': query,
        'search_performed': True,
        'search_time': spend_time
    }
    
    if results:
        template_vars.update({
            'results': results,
            'has_results': True
        })
    else:
        template_vars.update({
            'has_results': False,
            'no_results_message': f"No results found for '{query}'"
        })
    
    return render_template('search-results.html', **template_vars)

def perform_search(query):
    """执行Elasticsearch搜索"""
    if not es.index_exists() :
        print(f"索引 '{INDEX_NAME}' 未创建该索引")
        return None
    try:
        res = es.search_poetry(query)
        return res
    except Exception as e:
        print(f"搜索出错: {e}")
        return None



if __name__ == '__main__':
    start_elasticsearch()
    app.run(debug=True, port=5000)
    # * Running on http://127.0.0.1:5000