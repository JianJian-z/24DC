from elasticsearch import Elasticsearch

# 连接到 Elasticsearch
es = Elasticsearch("http://localhost:9200")

# **测试 IK 分词器**
def test_ik_analyzer():
    text = "明月几时有"
    analyzer = "ik_smart"  # 也可以换成 "ik_max_word"

    query_body = {
        "analyzer": analyzer,
        "text": text
    }

    try:
        response = es.indices.analyze(body=query_body)
        tokens = [token["token"] for token in response["tokens"]]
        print(f"分词结果 ({analyzer}): {tokens}")
    except Exception as e:
        print(f"分词器 {analyzer} 可能不可用，错误信息: {e}")

# **执行测试**
if __name__ == "__main__":
    test_ik_analyzer()
import subprocess
import sys
import time

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

if __name__ == "__main__":
    es_process = start_elasticsearch()
    # 使用完毕后终止进程
    # es_process.terminate()