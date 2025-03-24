from elasticsearch import Elasticsearch, helpers,ElasticsearchWarning
from elasticsearch.helpers import streaming_bulk, BulkIndexError
import json
import warnings
import time
from tqdm import tqdm
import  hashlib

# 忽略 Elasticsearch 警告
warnings.simplefilter('ignore', category=ElasticsearchWarning)
# 连接到 Elasticsearch（如果是本地，默认端口是 9200）
es = Elasticsearch(
    "http://localhost:9200",
    timeout=30,  # 连接超时时间为30秒
    max_retries=10,  
    retry_on_timeout=True  # 超时重试
)

# **1. 创建索引**
def create_index():
    index_config = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "ik_smart": {  # 使用 IK 分词器
                        "type": "custom",
                        "tokenizer": "ik_smart"
                    }
                }
            }
        },
            "mappings": {
            "dynamic": "strict",  # 禁止未定义的字段动态映,
            "properties": {
                "类型": {"type": "text", "analyzer": "ik_smart"},
                "古诗名": {"type": "keyword"},
                "作者": {"type": "text", "analyzer": "ik_smart"},
                "朝代":{"type": "text", "analyzer": "ik_smart"},
                "内容": {"type": "text", "analyzer": "ik_smart"},
                "译文":{"type": "text", "analyzer": "ik_smart"},
                "作者简介":{"type": "text", "analyzer": "ik_smart"},
                "鉴赏": {"type": "text", "analyzer": "ik_smart"},
                "赏析": {"type": "text", "analyzer": "ik_smart"},
                "简析":{"type": "text", "analyzer": "ik_smart"},
                "创作背景":{"type": "text", "analyzer": "ik_smart"},
                "注释":{"type": "object","dynamic": False},
            }
        }
    }
    
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
    es.indices.create(index=INDEX_NAME, body=index_config)
    print(f"索引 {INDEX_NAME} 创建成功")


def generate_id(text):
    """ 计算SHA-256哈希值，避免ID超长 """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def upload_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        poems = json.load(f)

    long_titles = []
    actions = []

    for poem in poems:
        poem_id = poem["古诗名"]
        if len(poem_id.encode("utf-8")) >= 512:
            long_titles.append(poem)
            # 用哈希值替代超长ID
            es_id = generate_id(poem_id)
        else:
            es_id = poem_id  # 保持原ID

        actions.append({
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": es_id,  
            "_source": poem
        })
    total_len = len(actions)
    failed_documents = []  # 用于存储失败的文档
    failed_file_name = json_file[:-5].split("/")[-1]
    
    record_time = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    error_file = f"failed_{INDEX_NAME}_{failed_file_name}_{record_time}.json"  
    try:
        with tqdm(total=total_len, desc="上传进度", unit="文档") as pbar:
            for success, info in streaming_bulk(es, actions, chunk_size=500):
                if not success:
                    failed_documents.append(info)
                pbar.update(1)  

        if failed_documents:
            # 将失败的文档写入 JSON 文件
            with open(error_file, "w", encoding="utf-8") as error_f:
                json.dump(failed_documents, error_f, ensure_ascii=False, indent=4)
            print(f"上传失败的文档已保存到 {error_file}")
        else:
            print(f"所有文档成功上传,共{total_len}条数据")

    except BulkIndexError as e:
        # 将失败的文档信息写入 JSON 文件
        with open(f"failed_record/{error_file}", "w", encoding="utf-8") as error_f:
            json.dump(long_titles, indent=4)
        print(f"上传失败数量{len(e.errors)} 文档已保存到 {error_file} ")

    if len(long_titles) > 0:
        with open(f"long_titles.json", "w", encoding="utf-8") as f:
            json.dump(long_titles, f, ensure_ascii=False, indent=4)
        print(f"有{len(long_titles)}条数据古诗名超长，已存入 long_titles.json备份")

def index_exists():
    return es.indices.exists(index=INDEX_NAME)


def search_poetry(query):
    if not index_exists():
        es.indices.create(index=INDEX_NAME)
        print(f"索引 '{INDEX_NAME}' 未创建该索引")
        return None

    query_body = {
        "query": {
            "match": {
                "内容": query  # 进行内容字段的模糊匹配
            }
        },
        "size": 10
    }
    
    # 搜索
    response = es.search(index=INDEX_NAME, body=query_body)
    
    print(f"==== 搜索 '{query}' 相关的诗词 ====")

    return response['hits']
# 删除索引
def delete_index(index_name):
    if es.indices.exists(index=index_name):
        # 删除索引
        es.indices.delete(index=index_name)
        print(f"索引 '{index_name}' 已删除")
    else:
        print(f"索引 '{index_name}' 不存在")


if __name__ == "__main__":
    
    # 指定索引名称
    #index_data_file = "datas/poems.json"
    index_data_file = "datas/result3.json"
    INDEX_NAME = index_data_file.split("/")[-1][:-5]

    #delete_index(INDEX_NAME)
    if input("是否创建索引/更新数据?[y/n]") == 'y':
        if not index_exists():
            es.indices.create(index=INDEX_NAME)
            print(f"索引 '{INDEX_NAME}' 未创建该索引")
            create_index()
            upload_data(index_data_file)
        else:
            print(f"索引 '{INDEX_NAME}' 已存在 更新数据")
            upload_data(index_data_file)
  
    while True:
        #search_poetry("明月精神")
        query = input("请输入查询内容(e 退出):")
        if query == "e":
            break
        t1= time.time()
        anw = search_poetry(query)
        spend_time = time.time()-t1
        
        for hit in anw['hits']:
            print(f"匹配得分: {hit['_score']}")
            print(f"标题: {hit['_source']['古诗名']}")
            print(f"作者: {hit['_source']['作者']}")
            print(f"内容: {hit['_source']['内容']}\n")
        print(f"共{len(anw)}条结果(top10) 耗时{spend_time}秒")
        print("="*40)
    
    print("**over**")