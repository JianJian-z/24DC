import json

def jaccard_similarity(str1, str2):
    set1, set2 = set(str1), set(str2)
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)

def fuzzy_match(query, corpus):
    similarities = []
    
    for idx, phrase in enumerate(corpus):
        similarity = jaccard_similarity(query, phrase)
        similarities.append((idx, phrase, similarity))
    
    # 按相似度排序，越相似的在前
    similarities.sort(key=lambda x: x[2], reverse=True)
    
    # 返回前20个匹配的成语及其在语料库中的索引
    top_10_matches = similarities[:20]
    return [(match[0], match[1]) for match in top_10_matches]  # 返回索引和成语

def get_details(words_list:list[tuple],is_poem=True):
    if is_poem:
        file = "datas/chengyu.json"
    else:
        file = "datas/poem.json"

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)  # 解析 JSON 文件

    # 提取成语字段并返回
    return [data[idx] for idx, _ in words_list]

def get_corpus_word():
    with open("datas/chengyu.json", "r", encoding="utf-8") as f:
        data = json.load(f)  # 解析 JSON 文件
    # 提取成语字段并返回
    return [item["成语"] for item in data]


corpus = get_corpus_word()
query = "安安"
match = fuzzy_match(query, corpus)
print(f"最相似的top10成语: {match}")
n = input("是否展示详细信息？(y/n)")
if n =="y":
    match_details = get_details(match)
    for unit in match_details:
        for key,value in unit.items():
            print(f"{key}: {value}")
        print()

