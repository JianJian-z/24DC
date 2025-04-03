#!/bin/bash

# 启动 Elasticsearch
echo "启动 Elasticsearch..."
elasticsearch #&  # 注意：`&` 是后台启动 Elasticsearch

# 等待 Elasticsearch 启动完毕
echo "等待 10 秒让 Elasticsearch 启动..."
sleep 10  # 等待 Elasticsearch 完全启动

# 启动 Flask Web 应用
echo "启动 Flask Web 应用..."
python app.py  # 启动你的 Web 应用
echo "Web 应用已启动!"
