# src/domain/chat/hybrid_search.py
"""
混合搜尋引擎
結合 BM25 (關鍵字) 與向量搜尋 (語義)
"""

from typing import List, Dict, Optional
from langchain.schema import Document
import jieba
import re


class ChineseTextPreprocessor:
    """中文文本預處理器"""
    
    def __init__(self):
        # 農業領域自定義詞典
        self.custom_dict = [
            # 農業技術
            "水稻", "病蟲害", "施肥", "灌溉", "育苗", "稻熱病", "紋枯病", "白葉枯病",
            "有機肥", "化學肥", "滴灌", "噴灌", "溫室", "大棚", "除草劑", "殺蟲劑",
            "農藥", "肥料", "種子", "秧苗", "收割", "播種", "插秧", "翻土",
            # 政策補助
            "補助", "申請", "資格", "流程", "審核", "撥款", "農會", "農保", "農機補助",
            "老農津貼", "農民健康保險", "農業天然災害救助", "休耕補助",
            # 業務相關
            "繼承", "存款", "繼承人", "證件", "戶籍謄本", "正本", "國民身分證",
            "除戶謄本", "親屬關係證明", "遺產分割協議書", "印鑑證明", "身分證影本"
        ]
        
        for word in self.custom_dict:
            jieba.add_word(word)
        
        # 停用詞表
        self.stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不',
            '人', '都', '一', '一個', '上', '也', '很', '到', '說',
            '要', '去', '你', '會', '著', '沒有', '看', '好',
            '這樣', '那樣', '如何', '什麼', '怎麼', '請問', '可以'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """
        中文分詞並過濾停用詞
        
        Args:
            text: 原始文本
            
        Returns:
            List[str]: 分詞結果
        """
        # 分詞
        words = jieba.lcut(text.lower())
        
        # 過濾停用詞和單字符
        filtered = [
            w for w in words 
            if w not in self.stopwords 
            and len(w) > 1 
            and not re.match(r'^[\W\d]+$', w)
        ]
        
        return filtered


class HybridSearchEngine:
    """混合搜尋引擎類別"""
    
    def __init__(self, bm25_weight: float = 0.5, vector_weight: float = 0.5):
        """
        初始化混合搜尋引擎
        
        Args:
            bm25_weight: BM25 權重
            vector_weight: 向量搜尋權重
        """
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.preprocessor = ChineseTextPreprocessor()
    
    def search(self, query: str, documents: List[Document], vector_scores: List[float], top_k: int = 5) -> List[Document]:
        """
        混合搜尋
        
        Args:
            query: 搜尋查詢
            documents: 文件列表
            vector_scores: 向量搜尋分數
            top_k: 返回數量
            
        Returns:
            List[Document]: 排序後的文件列表
        """
        # BM25 搜尋
        bm25_scores = self._bm25_search(query, documents)
        
        # 結合分數
        combined_scores = []
        for i in range(len(documents)):
            combined_score = (
                self.bm25_weight * bm25_scores[i] +
                self.vector_weight * vector_scores[i]
            )
            combined_scores.append((i, combined_score))
        
        # ✅ 修正：按分數排序（取元組的第二個元素）
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, _ in combined_scores[:top_k]]
        
        return [documents[i] for i in top_indices]
    
    def _bm25_search(self, query: str, documents: List[Document]) -> List[float]:
        """
        BM25 搜尋
        
        Args:
            query: 搜尋查詢
            documents: 文件列表
            
        Returns:
            List[float]: BM25 分數列表
        """
        # 分詞
        query_tokens = self.preprocessor.tokenize(query)
        
        # 計算 BM25 分數（簡化版）
        scores = []
        for doc in documents:
            doc_tokens = self.preprocessor.tokenize(doc.page_content)
            
            # 計算詞頻
            score = 0.0
            for token in query_tokens:
                tf = doc_tokens.count(token)
                if tf > 0:
                    # 簡化的 BM25 公式
                    score += tf / (tf + 1.0)
            
            scores.append(score)
        
        # 正規化
        max_score = max(scores) if scores else 1.0
        if max_score > 0:
            scores = [s / max_score for s in scores]
        
        return scores
