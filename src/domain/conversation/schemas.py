# src/domain/conversation/schemas.py
"""
對話領域相關的 Pydantic 模型定義
用於對話建立、更新、回應等數據驗證和序列化
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConversationCreate(BaseModel):
    """建立對話請求"""
    title: Optional[str] = Field("新對話", max_length=200, description="對話標題")


class ConversationUpdate(BaseModel):
    """更新對話請求"""
    title: Optional[str] = Field(None, max_length=200, description="對話標題")
    is_pinned: Optional[bool] = Field(None, description="是否置頂")
    is_archived: Optional[bool] = Field(None, description="是否封存")


class ConversationResponse(BaseModel):
    """對話資訊回應"""
    id: str
    title: Optional[str]
    message_count: int
    is_pinned: bool
    is_archived: bool
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """對話詳細資訊回應（簡化版，移除標籤和分享）"""
    id: str
    title: Optional[str]
    message_count: int
    is_pinned: bool
    is_archived: bool
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """聊天訊息回應"""
    role: str = Field(..., description="訊息角色（user/assistant）")
    content: str = Field(..., description="訊息內容")
    timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConversationSearchResult(BaseModel):
    """對話搜尋結果"""
    id: str
    title: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime


class ConversationFilter(BaseModel):
    """對話過濾條件"""
    include_archived: bool = False
    is_pinned: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
