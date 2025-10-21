# src/api/v1/conversations.py
"""
對話管理 API 路由（簡化版，移除標籤與分享功能）
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Optional

from ...domain.conversation.schemas import (
    ConversationCreate, ConversationUpdate, ConversationResponse, ConversationFilter
)
from ...domain.conversation.service import ConversationService
from ...domain.conversation.repository import ConversationRepository
from ...core.dependencies import get_current_user, get_db

router = APIRouter(prefix="/conversations", tags=["對話管理"])


def get_conversation_service(db=Depends(get_db)) -> ConversationService:
    """依賴注入：取得 ConversationService"""
    repo = ConversationRepository(db)
    return ConversationService(repo)


@router.post("/", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    建立新對話
    """
    conversation = conversation_service.create_conversation(
        current_user["id"],
        conversation_data.title
    )
    
    return {
        "message": "對話已建立",
        **conversation
    }


@router.get("/", response_model=List[Dict])
async def get_conversations(
    include_archived: bool = Query(False, description="是否包含已封存的對話"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    查詢用戶的對話列表
    """
    filters = ConversationFilter(include_archived=include_archived)
    conversations = conversation_service.list_user_conversations(
        current_user["id"],
        filters
    )
    
    return conversations


@router.get("/{conversation_id}", response_model=Dict)
async def get_conversation_detail(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    查詢對話詳細資訊
    """
    conversation = conversation_service.get_conversation_detail(
        conversation_id,
        current_user["id"]
    )
    
    return conversation


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新對話資訊
    """
    # 驗證所有權並更新
    if update_data.title is not None:
        result = conversation_service.update_conversation_title(
            conversation_id,
            current_user["id"],
            update_data.title
        )
        return result
    
    return {"message": "無更新"}


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    刪除對話
    """
    conversation_service.delete_conversation(conversation_id, current_user["id"])


@router.post("/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    封存/取消封存對話
    """
    result = conversation_service.toggle_archive(conversation_id, current_user["id"])
    return result


@router.post("/{conversation_id}/pin")
async def pin_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    置頂/取消置頂對話
    """
    result = conversation_service.toggle_pin(conversation_id, current_user["id"])
    return result


@router.get("/search/", response_model=Dict)
async def search_conversations(
    query: str = Query(..., min_length=1, description="搜尋關鍵字"),
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    搜尋對話
    """
    results = conversation_service.search_conversations(current_user["id"], query)
    return results
