# src/domain/chat/service.py
"""
聊天業務邏輯層 (Service)
處理聊天相關的業務邏輯，協調 Repository、RAG Engine 與外部服務
"""

from typing import Dict, Optional, List, AsyncGenerator
from fastapi import HTTPException, status
from .repository import ChatRepository
from .schemas import ChatRequest, ChatResponse, ChatSource, IntentResult
from .rag_engine import RAGEngine
from .intent_classifier import IntentClassifier


class ChatService:
    """聊天業務邏輯類別"""
    
    def __init__(self, repository: ChatRepository, rag_engine: RAGEngine,
                 intent_classifier: IntentClassifier):
        """
        初始化 Service
        
        Args:
            repository: ChatRepository 實例
            rag_engine: RAG 引擎
            intent_classifier: 意圖分類器
        """
        self.repo = repository
        self.rag = rag_engine
        self.classifier = intent_classifier
    
    def process_query(self, request: ChatRequest, user_id: int) -> ChatResponse:
        """
        處理聊天查詢（REST API）
        
        Args:
            request: 聊天請求
            user_id: 用戶 ID
            
        Returns:
            ChatResponse: 聊天回應
        """
        # 意圖分類
        intent_result = self.classifier.classify(request.question)
        
        # 載入對話歷史
        history_context = ""
        if request.conversation_id:
            history = self.repo.get_recent_history(request.conversation_id, limit=10)
            if history:
                history_context = self._format_history(history)
        
        # 根據意圖決定處理方式
        if intent_result["type"] == "out_of_scope":
            answer = self._handle_out_of_scope()
            sources = []
        elif intent_result["use_rag"]:
            answer, sources = self._process_with_rag(
                request.question, history_context, request.k
            )
        else:
            answer = self._process_chitchat(request.question, history_context)
            sources = []
        
        # 儲存對話記錄
        if request.conversation_id:
            self.repo.save_message(request.conversation_id, "user", request.question)
            self.repo.save_message(
                request.conversation_id, "assistant", answer,
                sources=[s.dict() for s in sources],
                intent=intent_result
            )
            self.repo.update_conversation_stats(request.conversation_id, user_id)
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            context_count=len(sources),
            conversation_id=request.conversation_id,
            intent=intent_result
        )
    
    async def process_streaming_query(self, request: ChatRequest, 
                                      user_id: int) -> AsyncGenerator[Dict, None]:
        """
        處理串流聊天查詢
        
        Args:
            request: 聊天請求
            user_id: 用戶 ID
            
        Yields:
            Dict: 串流回應片段
        """
        # 意圖分類
        intent_result = self.classifier.classify(request.question)
        yield {"type": "intent", "data": intent_result}
        
        # 載入對話歷史
        history_context = ""
        if request.conversation_id:
            history = self.repo.get_recent_history(request.conversation_id, limit=10)
            if history:
                history_context = self._format_history(history)
        
        # 串流生成回答
        full_response = ""
        sources = []
        
        if intent_result["type"] == "out_of_scope":
            answer = self._handle_out_of_scope()
            for char in answer:
                yield {"type": "chunk", "content": char}
                full_response += char
        elif intent_result["use_rag"]:
            async for chunk in self.rag.generate_stream(
                request.question, history_context, request.k
            ):
                if chunk["type"] == "chunk":
                    full_response += chunk["content"]
                elif chunk["type"] == "sources":
                    sources = chunk["sources"]
                yield chunk
        else:
            async for chunk in self.rag.generate_chitchat_stream(
                request.question, history_context
            ):
                full_response += chunk["content"]
                yield chunk
        
        # 儲存對話記錄
        if request.conversation_id:
            self.repo.save_message(request.conversation_id, "user", request.question)
            self.repo.save_message(
                request.conversation_id, "assistant", full_response,
                sources=sources, intent=intent_result
            )
            self.repo.update_conversation_stats(request.conversation_id, user_id)
        
        yield {"type": "done", "sources": sources}
    
    def get_conversation_history(self, conversation_id: str, user_id: int,
                                limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        取得對話歷史
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 聊天記錄
        """
        messages = self.repo.get_chat_history(conversation_id, limit, offset)
        
        # 格式化回應
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["created_at"].isoformat(),
                "sources": msg.get("sources"),
                "intent": msg.get("intent")
            })
        
        return formatted_messages
    
    def clear_conversation_history(self, conversation_id: str, user_id: int):
        """
        清空對話歷史
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
        """
        self.repo.clear_chat_history(conversation_id)
    
    def _format_history(self, history: List[tuple]) -> str:
        """格式化對話歷史為文字"""
        formatted = "\n【歷史對話】\n"
        for role, content in history:
            prefix = "用戶" if role == "user" else "AI"
            formatted += f"{prefix}: {content}\n"
        return formatted + "\n"
    
    def _handle_out_of_scope(self) -> str:
        """處理超出範圍的問題"""
        return """抱歉，這個問題超出了我的服務範圍。😊

我主要協助以下領域的問題：
• 🌾 農業技術諮詢（種植、病蟲害、施肥等）
• 💰 農業政策與補助申請
• 📋 農會相關業務查詢
• 🔍 農業文件資料查詢

您可以換個與農業相關的問題試試看！"""
    
    def _process_with_rag(self, question: str, history: str, k: int) -> tuple:
        """使用 RAG 處理問題"""
        result = self.rag.query(question, history, k)
        sources = [
            ChatSource(
                source=doc["source"],
                department=doc.get("department", ""),
                content=doc["content"]
            )
            for doc in result.get("sources", [])
        ]
        return result["answer"], sources
    
    def _process_chitchat(self, question: str, history: str) -> str:
        """處理閒聊"""
        return self.rag.chitchat(question, history)
