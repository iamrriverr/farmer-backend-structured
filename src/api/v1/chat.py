# src/api/v1/chat.py
"""
聊天 API 路由
處理 REST API 查詢、串流查詢、WebSocket 連線
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Dict, List
import json

from ...domain.chat.schemas import ChatRequest, ChatResponse
from ...domain.chat.service import ChatService
from ...domain.chat.repository import ChatRepository
from ...domain.chat.rag_engine import RAGEngine
from ...domain.chat.intent_classifier import IntentClassifier
from ...infrastructure.vector_store import VectorStoreManager
from ...core.dependencies import get_current_user, get_db, verify_websocket_token
from ...core.config import Config

router = APIRouter(prefix="/chat", tags=["聊天"])


def get_vector_store() -> VectorStoreManager:
    """依賴注入：取得 VectorStoreManager"""
    return VectorStoreManager(Config)


def get_rag_engine(vector_store: VectorStoreManager = Depends(get_vector_store)) -> RAGEngine:
    """依賴注入：取得 RAGEngine"""
    return RAGEngine(vector_store, Config)


def get_intent_classifier() -> IntentClassifier:
    """依賴注入：取得 IntentClassifier"""
    return IntentClassifier(Config)


def get_chat_service(
    db=Depends(get_db),
    rag_engine: RAGEngine = Depends(get_rag_engine),
    intent_classifier: IntentClassifier = Depends(get_intent_classifier)
) -> ChatService:
    """依賴注入：取得 ChatService"""
    repo = ChatRepository(db)
    return ChatService(repo, rag_engine, intent_classifier)


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    聊天查詢（REST API，非串流）
    
    - **question**: 問題內容
    - **conversation_id**: 對話 ID（選填，用於記憶上下文）
    - **k**: RAG 檢索數量（預設 5）
    """
    response = chat_service.process_query(request, current_user["id"])
    return response


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    聊天查詢（串流模式）
    
    使用 Server-Sent Events (SSE) 返回串流回應
    """
    async def generate():
        try:
            async for chunk in chat_service.process_streaming_query(
                request, current_user["id"]
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_chunk = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(..., description="JWT Token"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    WebSocket 聊天端點
    
    支援即時雙向通訊
    """
    # 驗證 Token
    try:
        user = await verify_websocket_token(token)
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await websocket.accept()
    
    try:
        while True:
            # 接收用戶訊息
            data = await websocket.receive_json()
            
            # 解析請求
            question = data.get("content", "")
            k = data.get("k", 5)
            
            if not question:
                await websocket.send_json({
                    "type": "error",
                    "message": "問題不能為空"
                })
                continue
            
            # 建立請求
            request = ChatRequest(
                question=question,
                conversation_id=conversation_id,
                k=k
            )
            
            # 串流回應
            async for chunk in chat_service.process_streaming_query(
                request, user["id"]
            ):
                await websocket.send_json(chunk)
    
    except WebSocketDisconnect:
        print(f"WebSocket 連線已關閉: {conversation_id}")
    except Exception as e:
        print(f"WebSocket 錯誤: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@router.get("/history/{conversation_id}", response_model=List[Dict])
async def get_chat_history(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    取得對話歷史記錄
    """
    messages = chat_service.get_conversation_history(
        conversation_id,
        current_user["id"],
        limit,
        offset
    )
    
    return messages


@router.delete("/history/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    清空對話歷史記錄
    """
    chat_service.clear_conversation_history(conversation_id, current_user["id"])
