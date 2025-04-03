'''
author       : 渐渐
Date         : 2025-03-31 14:19:08
LastEditTime : 2025-04-03 16:09:22
'''
from flask import Flask, render_template, request, redirect, url_for, jsonify 
from elasticsearch import Elasticsearch, ElasticsearchWarning
import warnings
import time
import requests
from dotenv import load_dotenv
import os
import json

app = Flask(__name__, template_folder='template', static_folder='static')

# 忽略 Elasticsearch 警告
warnings.simplefilter('ignore', category=ElasticsearchWarning)

# 配置Elasticsearch连接
es = Elasticsearch(
    "http://localhost:9200",
    timeout=30,
    max_retries=10,
    retry_on_timeout=True
)

# 索引名称
INDEX_NAME = "poetry_index"

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
    if not es.indices.exists(index=INDEX_NAME):
        return None
    query_body = {
        "query": {
            "match": {
                "内容": query  # 进行内容字段的模糊匹配
            }
        },
        "size": 10
    }
    
    try:
        res = es.search(index=INDEX_NAME, body=query_body)['hits']['hits']
        print(res)
        return res
    except Exception as e:
        print(f"搜索出错: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, port=5000)