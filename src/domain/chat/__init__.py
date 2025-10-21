# src/domain/chat/__init__.py
"""
聊天領域模組
包含聊天相關的 Schema、Repository、Service、RAG Engine 等
"""

from .schemas import (
    ChatRequest,
    ChatSource,
    ChatResponse,
    ChatMessageResponse,
    IntentResult,
    WebSocketMessage,
    StreamChunk
)
from .repository import ChatRepository
from .service import ChatService
from .rag_engine import RAGEngine
from .intent_classifier import IntentClassifier
from .hybrid_search import HybridSearchEngine, ChineseTextPreprocessor

__all__ = [
    # Schemas
    "ChatRequest",
    "ChatSource",
    "ChatResponse",
    "ChatMessageResponse",
    "IntentResult",
    "WebSocketMessage",
    "StreamChunk",
    
    # Repository & Service
    "ChatRepository",
    "ChatService",
    
    # RAG Components
    "RAGEngine",
    "IntentClassifier",
    "HybridSearchEngine",
    "ChineseTextPreprocessor"
]
