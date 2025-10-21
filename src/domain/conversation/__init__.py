# src/domain/conversation/__init__.py
"""
對話領域模組
包含對話相關的 Schema、Repository、Service
"""

from .schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetail,
    ChatMessageResponse,
    ConversationSearchResult,
    ConversationFilter
)
from .repository import ConversationRepository
from .service import ConversationService

__all__ = [
    # Schemas
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationDetail",
    "ChatMessageResponse",
    "ConversationSearchResult",
    "ConversationFilter",
    
    # Repository & Service
    "ConversationRepository",
    "ConversationService"
]
