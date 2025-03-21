import json
import re
from fuzzywuzzy import fuzz, process

class PoemSearcher:
    def __init__(self, json_path):
        self.poems = self._load_data(json_path)
        self.processed_data = self._preprocess_data()

    def _load_data(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _clean_text(self, text):
        """清洗文本 去除不属于字母、数字、下划线以及中文字符\u4e00-\u9fff的字符"""
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        return text.strip().lower()

    def _preprocess_data(self):
        """匹配时忽略标点符号的新版预处理"""
        processed = []
        for poem in self.poems:
            # 直接遍历诗句列表，不再需要split分割
            for line in poem.get('内容', []):  
                # 清洗并验证诗句有效性
                clean_line = self._clean_text(line)
                
                # 过滤无效诗句（至少包含4个汉字）
                if len(clean_line) >= 4:
                    processed.append({
                        'text': clean_line,
                        'original': poem,
                        # 可选：保留原始带标点的文本用于展示
                        'original_line': line.strip("，。")  
                    })
        return processed

    def _calculate_score(self, query, target):
        """
        自定义评分规则（满分100）
        - 完全匹配：100
        - 连续匹配：根据最长连续匹配比例
        - 散列匹配：根据匹配字符数惩罚
        """
        # 完全匹配检测
        if query == target:
            return 100
        
        # 最长连续子串检测
        longest_match = 0
        for i in range(len(query)):
            for j in range(i+1, len(query)+1):
                substring = query[i:j]
                if substring in target:
                    longest_match = max(longest_match, j-i)
        
        # 计算连续匹配得分（权重70%）
        continuity_score = (longest_match / len(query)) * 70
        
        # 计算字符覆盖率得分（权重30%）
        common_chars = set(query) & set(target)
        coverage_score = (len(common_chars) / len(query)) * 30
        
        # 综合得分（最高不超过95，保留5分给完全匹配）
        total_score = min(continuity_score + coverage_score, 95)
        
        return round(total_score, 1)

    def search(self, query, top_n=5, min_score=60):
        """改进版搜索算法"""
        query_clean = self._clean_text(query)
        if not query_clean:
            return []

        candidates = [(item['text'], idx) for idx, item in enumerate(self.processed_data)]
        
        results = []
        for cand_text, idx in candidates:
            # 使用自定义评分
            score = self._calculate_score(query_clean, cand_text)
            if score >= min_score:
                results.append((cand_text, score, idx))
        
        # 按得分排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 去重处理（同原逻辑）
        seen_titles = set()
        final_results = []
        for cand_text, score, idx in results:
            poem = self.processed_data[idx]['original']
            title = poem['古诗名']
            if title not in seen_titles:
                seen_titles.add(title)
                final_results.append({
                    'title': title,
                    'score': score,
                    'matched_sentence': self.processed_data[idx]['original_line'],
                    'full_content': "\n".join(poem['内容'])
                })
            if len(final_results) >= top_n:
                break
        
        return final_results[:top_n]

# 测试
if __name__ == "__main__":
    searcher = PoemSearcher("datas/result3.json")
    test_queries = ["夜来风雨", "云随凤", "千里目更上", "春棉不覺晓"]
    import time
    for query in test_queries:
        print(f"查询: '{query}'")
        t1 = time.time()
        results = searcher.search(query)
        print(f" 时长{time.time()-t1:.2f}秒")
        for i, res in enumerate(results, 1):
            print(f"{i}. 《{res['title']}》-  (匹配度: {res['score']}%)")
            print(f"   匹配句: {res['matched_sentence']}")
            print(f"   全文: {res['full_content']}")
            
        print("\n" + "="*50 + "\n")