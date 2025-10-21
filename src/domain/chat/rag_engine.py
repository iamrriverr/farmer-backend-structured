# src/domain/chat/rag_engine.py
"""
RAG 引擎核心
負責檢索增強生成 (Retrieval-Augmented Generation) 的核心邏輯
整合 LLMConfig 和 PromptTemplates 實現配置分離
"""

from typing import Dict, Optional, List, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import Document
import asyncio

# 導入新的配置模組
from ...core.config import LLMConfig, PromptTemplates


class RAGEngine:
    """RAG 引擎類別"""
    
    def __init__(self, vector_store_manager, config):
        """
        初始化 RAG 引擎
        
        Args:
            vector_store_manager: 向量儲存管理器
            config: 配置物件（保留向後相容）
        """
        self.vector_store = vector_store_manager
        self.config = config
        
        # 使用 LLMConfig 初始化 LLM
        self._init_llm()
        
        # 使用 PromptTemplates 初始化 Prompt
        self._init_prompts()
    
    def _init_llm(self):
        """初始化 LLM 模型（使用 LLMConfig）"""
        if LLMConfig.PRIMARY_LLM == "gpt":
            # GPT 模型（非串流）
            self.llm = ChatOpenAI(
                model=LLMConfig.GPT_MODEL,
                openai_api_key=LLMConfig.OPENAI_API_KEY,
                temperature=LLMConfig.TEMPERATURE,
                max_tokens=LLMConfig.MAX_TOKENS,
                top_p=LLMConfig.TOP_P,
                frequency_penalty=LLMConfig.FREQUENCY_PENALTY,
                presence_penalty=LLMConfig.PRESENCE_PENALTY,
                streaming=False
            )
            
            # GPT 模型（串流）
            self.stream_llm = ChatOpenAI(
                model=LLMConfig.GPT_MODEL,
                openai_api_key=LLMConfig.OPENAI_API_KEY,
                temperature=LLMConfig.TEMPERATURE,
                max_tokens=LLMConfig.MAX_TOKENS,
                top_p=LLMConfig.TOP_P,
                frequency_penalty=LLMConfig.FREQUENCY_PENALTY,
                presence_penalty=LLMConfig.PRESENCE_PENALTY,
                streaming=True
            )
            
        else:  # Gemini
            # Gemini 模型（非串流）
            self.llm = ChatGoogleGenerativeAI(
                model=LLMConfig.GEMINI_MODEL,
                google_api_key=LLMConfig.GOOGLE_API_KEY,
                temperature=LLMConfig.TEMPERATURE,
                max_output_tokens=LLMConfig.MAX_TOKENS
            )
            
            # Gemini 模型（串流）
            self.stream_llm = ChatGoogleGenerativeAI(
                model=LLMConfig.GEMINI_MODEL,
                google_api_key=LLMConfig.GOOGLE_API_KEY,
                temperature=LLMConfig.TEMPERATURE,
                max_output_tokens=LLMConfig.MAX_TOKENS,
                streaming=True
            )
    
    def _init_prompts(self):
        """初始化 Prompt 模板（使用 PromptTemplates）"""
        # RAG Prompt
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system", PromptTemplates.RAG_SYSTEM_PROMPT),
            ("human", PromptTemplates.RAG_HUMAN_PROMPT)
        ])
        
        # Chitchat Prompt
        self.chitchat_prompt = ChatPromptTemplate.from_messages([
            ("system", PromptTemplates.CHITCHAT_SYSTEM_PROMPT),
            ("human", PromptTemplates.CHITCHAT_HUMAN_PROMPT)
        ])
    
    def query(self, question: str, history: str = "", k: int = 5, 
              metadata_filter: Optional[Dict] = None) -> Dict:
        """
        RAG 查詢（非串流）
        
        Args:
            question: 用戶問題
            history: 對話歷史
            k: 檢索數量
            metadata_filter: metadata 過濾條件
            
        Returns:
            Dict: 包含答案和來源的結果
        """
        # 向量檢索
        search_results = self.vector_store.search(
            query_text=question,
            n_results=k,
            where=metadata_filter
        )
        
        # 格式化上下文和來源
        context_docs, sources = self._process_search_results(search_results)
        context = self._format_context(context_docs)
        
        # 生成答案
        chain = self.rag_prompt | self.llm
        response = chain.invoke({
            "context": context,
            "history": history,
            "question": question
        })
        
        return {
            "answer": response.content,
            "sources": sources,
            "context_count": len(context_docs)
        }
    
    async def generate_stream(self, question: str, history: str = "", k: int = 5,
                             metadata_filter: Optional[Dict] = None) -> AsyncGenerator[Dict, None]:
        """
        RAG 串流查詢
        
        Args:
            question: 用戶問題
            history: 對話歷史
            k: 檢索數量
            metadata_filter: metadata 過濾條件
            
        Yields:
            Dict: 串流回應片段
        """
        # 檢查串流是否啟用
        if not LLMConfig.ENABLE_STREAMING:
            # 如果串流被停用，回退到非串流模式
            result = self.query(question, history, k, metadata_filter)
            yield {"type": "sources", "sources": result["sources"]}
            yield {"type": "answer", "content": result["answer"]}
            return
        
        # 向量檢索
        search_results = self.vector_store.search(
            query_text=question,
            n_results=k,
            where=metadata_filter
        )
        
        # 格式化上下文和來源
        context_docs, sources = self._process_search_results(search_results)
        
        # 先發送來源
        yield {"type": "sources", "sources": sources}
        
        # 格式化上下文
        context = self._format_context(context_docs)
        
        # 串流生成答案
        chain = self.rag_prompt | self.stream_llm
        
        chunk_index = 0
        async for chunk in chain.astream({
            "context": context,
            "history": history,
            "question": question
        }):
            if hasattr(chunk, 'content') and chunk.content:
                yield {
                    "type": "chunk",
                    "content": chunk.content,
                    "chunk_index": chunk_index
                }
                chunk_index += 1
    
    def chitchat(self, question: str, history: str = "") -> str:
        """
        閒聊回應（非串流）
        
        Args:
            question: 用戶問題
            history: 對話歷史
            
        Returns:
            str: AI 回應
        """
        chain = self.chitchat_prompt | self.llm
        response = chain.invoke({
            "history": history,
            "question": question
        })
        
        return response.content
    
    async def generate_chitchat_stream(self, question: str, 
                                      history: str = "") -> AsyncGenerator[Dict, None]:
        """
        閒聊串流回應
        
        Args:
            question: 用戶問題
            history: 對話歷史
            
        Yields:
            Dict: 串流回應片段
        """
        # 檢查串流是否啟用
        if not LLMConfig.ENABLE_STREAMING:
            # 回退到非串流模式
            answer = self.chitchat(question, history)
            yield {"type": "answer", "content": answer}
            return
        
        chain = self.chitchat_prompt | self.stream_llm
        
        chunk_index = 0
        async for chunk in chain.astream({
            "history": history,
            "question": question
        }):
            if hasattr(chunk, 'content') and chunk.content:
                yield {
                    "type": "chunk",
                    "content": chunk.content,
                    "chunk_index": chunk_index
                }
                chunk_index += 1
    
    def _process_search_results(self, search_results: Dict) -> tuple:
        """
        處理搜尋結果
        
        Args:
            search_results: 向量搜尋結果
            
        Returns:
            tuple: (context_docs, sources)
        """
        context_docs = []
        sources = []
        
        if search_results and 'documents' in search_results:
            for i, doc in enumerate(search_results['documents'][0]):
                metadata = search_results['metadatas'][0][i] if 'metadatas' in search_results else {}
                
                context_docs.append({
                    'content': doc,
                    'metadata': metadata
                })
                
                sources.append({
                    'source': metadata.get('source', 'unknown'),
                    'department': metadata.get('department', ''),
                    'content': doc[:200] + '...' if len(doc) > 200 else doc
                })
        
        return context_docs, sources
    
    def _format_context(self, docs: List[Dict]) -> str:
        """
        格式化檢索結果為上下文字串
        
        Args:
            docs: 文件列表
            
        Returns:
            str: 格式化的上下文
        """
        if not docs:
            return "（無相關資料）"
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc['content']
            metadata = doc.get('metadata', {})
            
            source = metadata.get('source', 'unknown')
            department = metadata.get('department', '')
            
            context_part = f"【資料 {i}】"
            if source:
                context_part += f"\n來源：{source}"
            if department:
                context_part += f"\n部門：{department}"
            context_part += f"\n內容：\n{content}\n"
            
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    def get_model_info(self) -> dict:
        """
        取得當前使用的模型資訊
        
        Returns:
            dict: 模型資訊
        """
        return LLMConfig.get_model_info()
    
    def update_temperature(self, temperature: float):
        """
        動態調整 Temperature
        
        Args:
            temperature: 新的 temperature 值 (0.0-1.0)
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature 必須介於 0.0 和 1.0 之間")
        
        # 更新 LLM 的 temperature
        self.llm.temperature = temperature
        self.stream_llm.temperature = temperature
        
        print(f"✅ Temperature 已更新為 {temperature}")
