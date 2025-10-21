# src/domain/chat/intent_classifier.py
"""
意圖分類器（增強版）
LLM + Rule-Based 雙重判斷，帶信心度閾值調整
"""

from typing import Dict, Literal
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
import json

# 導入配置
from ...core.config import LLMConfig, PromptTemplates


class IntentClassification(BaseModel):
    """意圖分類結果"""
    type: Literal["RAG", "CHITCHAT", "OUT_OF_SCOPE"] = Field(
        description="分類類型：RAG（需檢索）、CHITCHAT（閒聊）、OUT_OF_SCOPE（超範圍）"
    )
    confidence: float = Field(
        description="信心分數（0.0-1.0）",
        default=0.8
    )
    reason: str = Field(
        description="分類理由"
    )


class IntentClassifier:
    """意圖分類器（LLM + Rule-Based）"""
    
    # ✅ 配置閾值（可調整）
    CONFIDENCE_THRESHOLD = 0.7  # 信心度低於此值時使用規則引擎
    
    def __init__(self, config):
        """初始化意圖分類器"""
        self.config = config
        
        # 使用 JsonOutputParser
        self.output_parser = JsonOutputParser(pydantic_object=IntentClassification)
        
        # 初始化 LLM
        self._init_classifier_llm()
        
        # 初始化 Prompt
        self._init_prompt()
    
    def _init_classifier_llm(self):
        """初始化分類器 LLM"""
        if LLMConfig.PRIMARY_LLM == "gpt":
            self.classifier_llm = ChatOpenAI(
                model="gpt-4.1-nano",
                openai_api_key=LLMConfig.OPENAI_API_KEY,
                temperature=0.0,
                max_tokens=500
            )
        else:  # gemini
            self.classifier_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-8b",
                google_api_key=LLMConfig.GOOGLE_API_KEY,
                temperature=0.0
            )
    
    def _init_prompt(self):
        """初始化 Prompt 模板"""
        format_instructions = self.output_parser.get_format_instructions()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一個語言意圖分析專家，負責判斷用戶問題是否需要使用文件檢索來回答。\n\n"
             "將用戶問題分類為 RAG, CHITCHAT, or OUT_OF_SCOPE.\n\n"
             f"{format_instructions}"),
            ("user", "{question}")
        ])
    
    def _rule_based_classify(self, query: str) -> Dict:
        """
        基於規則的意圖分類（備用方案）
        當 LLM 分類不確定時使用
        """
        query_lower = query.lower().strip()
        
        # ============================================================
        # 規則 1：問候語和禮貌用語 → CHITCHAT
        # ============================================================
        greetings = [
            "你好", "您好", "hi", "hello", "嗨", 
            "早安", "午安", "晚安", "早上好", "晚上好"
        ]
        if any(g in query_lower for g in greetings) and len(query) < 10:
            return {
                "use_rag": False,
                "type": "chitchat",
                "confidence": 0.95,
                "reason": "規則匹配：問候語"
            }
        
        # ============================================================
        # 規則 2：感謝和禮貌回應 → CHITCHAT
        # ============================================================
        thanks = [
            "謝謝", "感謝", "謝了", "多謝", "thx", "thanks",
            "好的", "ok", "知道了", "明白", "了解", "收到"
        ]
        if any(t in query_lower for t in thanks) and len(query) < 15:
            return {
                "use_rag": False,
                "type": "chitchat",
                "confidence": 0.95,
                "reason": "規則匹配：禮貌用語"
            }
        
        # ============================================================
        # 規則 3：農會業務關鍵字 → RAG（高優先級）
        # ============================================================
        business_keywords = [
            # 貸款相關
            "貸款", "信貸", "借款", "利率", "利息", "還款", "額度",
            # 保險相關
            "保險", "投保", "理賠", "保費", "保單",
            # 補助相關
            "補助", "補貼", "獎勵", "津貼",
            # 農業相關
            "農機", "農具", "肥料", "農藥", "種子",
            "有機", "認證", "檢驗",
            # 業務流程
            "申請", "辦理", "手續", "文件", "證明", "資格",
            "條件", "規定", "辦法", "流程", "步驟", "繼承"
        ]
        
        if any(k in query for k in business_keywords):
            return {
                "use_rag": True,
                "type": "rag",
                "confidence": 0.90,
                "reason": "規則匹配：業務關鍵字"
            }
        
        # ============================================================
        # 規則 4：疑問詞 + 長度 → RAG
        # ============================================================
        question_words = [
            "如何", "怎麼", "怎樣", "怎麽", "怎么",
            "什麼", "什么", "哪裡", "哪里", "哪些",
            "為什麼", "為何", "幾時", "何時"
        ]
        
        if any(q in query for q in question_words) and len(query) > 5:
            return {
                "use_rag": True,
                "type": "rag",
                "confidence": 0.80,
                "reason": "規則匹配：疑問詞"
            }
        
        # ============================================================
        # 規則 5：閒聊話題 → CHITCHAT
        # ============================================================
        chitchat_topics = [
            "天氣", "氣溫", "下雨", "晴天",
            "時間", "日期", "星期",
            "心情", "累", "開心", "難過"
        ]
        
        if any(topic in query for topic in chitchat_topics):
            return {
                "use_rag": False,
                "type": "chitchat",
                "confidence": 0.85,
                "reason": "規則匹配：閒聊話題"
            }
        
        # ============================================================
        # 規則 6：超出範圍的話題 → OUT_OF_SCOPE
        # ============================================================
        out_of_scope_keywords = [
            "股票", "基金", "投資", "理財",
            "醫療", "看病", "藥物", "治療",
            "法律", "訴訟", "律師",
            "寫作", "小說", "詩歌"
        ]
        
        if any(k in query for k in out_of_scope_keywords):
            return {
                "use_rag": False,
                "type": "out_of_scope",
                "confidence": 0.90,
                "reason": "規則匹配：超出業務範圍"
            }
        
        # ============================================================
        # 預設：使用 RAG（保守策略）
        # ============================================================
        return {
            "use_rag": True,
            "type": "rag",
            "confidence": 0.70,
            "reason": "規則匹配：預設使用 RAG"
        }
    
    def classify(self, query: str) -> Dict:
        """
        對查詢進行意圖分類（主方法）
        策略：LLM 優先，信心度不足時使用規則引擎
        
        Args:
            query: 用戶查詢
            
        Returns:
            Dict: 分類結果
        """
        try:
            # ============================================================
            # Step 1: 嘗試使用 LLM 分類
            # ============================================================
            chain = self.prompt | self.classifier_llm | self.output_parser
            result = chain.invoke({"question": query})
            
            intent_type = result.get("type", "RAG").upper()
            confidence = result.get("confidence", 0.8)
            reason = result.get("reason", "")
            
            # ============================================================
            # Step 2: 檢查信心度
            # ============================================================
            if confidence < self.CONFIDENCE_THRESHOLD:
                print(f"⚠️ LLM 信心度不足({confidence:.2f})，切換到規則引擎")
                return self._rule_based_classify(query)
            
            # ============================================================
            # Step 3: 關鍵字強制覆蓋（雙重保險）
            # ============================================================
            
            # 強制 RAG 關鍵字
            force_rag_keywords = ["貸款", "補助", "保險", "申請", "流程"]
            if any(k in query for k in force_rag_keywords):
                intent_type = "RAG"
                reason = f"關鍵字覆蓋：{reason}"
            
            # 強制 CHITCHAT 關鍵字
            force_chitchat_keywords = ["你好", "謝謝", "再見"]
            if any(k in query for k in force_chitchat_keywords) and len(query) < 10:
                intent_type = "CHITCHAT"
                reason = f"關鍵字覆蓋：{reason}"
            
            # ============================================================
            # Step 4: 返回結果
            # ============================================================
            return {
                "use_rag": intent_type == "RAG",
                "type": intent_type.lower(),
                "confidence": confidence,
                "reason": f"LLM分類 - {reason}"
            }
            
        except Exception as e:
            # ============================================================
            # 錯誤處理：直接使用規則引擎
            # ============================================================
            print(f"⚠️ LLM 分類失敗: {e}，使用規則引擎")
            return self._rule_based_classify(query)
    
    def extract_metadata_filter(self, query: str) -> Dict:
        """從查詢中提取 metadata 過濾條件"""
        import re
        metadata_filter = {}
        
        # 部門關鍵字
        department_keywords = {
            "credit": ["credit", "loan", "貸款", "信貸"],
            "insurance": ["insurance", "保險"],
            "supply": ["supply", "purchase", "採購", "供應"],
            "promotion": ["promotion", "education", "培訓", "推廣"]
        }
        
        for dept, keywords in department_keywords.items():
            if any(keyword in query.lower() for keyword in keywords):
                metadata_filter["department"] = dept
                break
        
        # 年份提取
        year_pattern = r'(\b(19|20)\d{2}\b)|(\d{4}年)'
        year_match = re.search(year_pattern, query)
        if year_match:
            year_str = year_match.group().replace('年', '')
            metadata_filter["year"] = int(year_str)
        
        return metadata_filter
