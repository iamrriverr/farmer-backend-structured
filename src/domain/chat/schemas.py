# src/domain/chat/schemas.py
"""
聊天領域相關的 Pydantic 模型定義
用於聊天請求、回應等數據驗證和序列化
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """聊天請求"""
    question: str = Field(..., min_length=1, max_length=2000, description="問題內容")
    conversation_id: Optional[str] = Field(None, description="對話 ID（用於記憶）")
    k: int = Field(5, ge=1, le=20, description="RAG 檢索數量")


class ChatSource(BaseModel):
    """聊天來源文件"""
    source: str = Field(..., description="來源文件名稱")
    department: Optional[str] = Field("", description="部門")
    content: str = Field(..., description="相關內容片段")


class ChatResponse(BaseModel):
    """聊天回應"""
    answer: str = Field(..., description="AI 回答")
    sources: List[ChatSource] = Field(default_factory=list, description="來源文件列表")
    context_count: int = Field(0, description="使用的上下文數量")
    conversation_id: Optional[str] = None
    intent: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """聊天訊息回應"""
    role: str = Field(..., description="訊息角色（user/assistant）")
    content: str = Field(..., description="訊息內容")
    timestamp: Optional[datetime] = None
    sources: Optional[List[ChatSource]] = None
    
    class Config:
        from_attributes = True


class IntentResult(BaseModel):
    """意圖分類結果"""
    use_rag: bool = Field(..., description="是否使用 RAG")
    type: str = Field(..., description="意圖類型（rag/chitchat/out_of_scope）")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reason: str = Field(..., description="判斷原因")


class WebSocketMessage(BaseModel):
    """WebSocket 訊息格式"""
    type: str = Field(..., description="訊息類型")
    content: Optional[str] = None
    k: Optional[int] = Field(5, ge=1, le=20)


class StreamChunk(BaseModel):
    """串流回應片段"""
    type: str = "chunk"
    content: str
    chunk_index: int
