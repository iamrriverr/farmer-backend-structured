# tests/test_api/test_chat.py
"""
測試聊天 API
"""

import pytest
from unittest.mock import patch, Mock


class TestChatQuery:
    """測試聊天查詢"""
    
    @patch('src.domain.chat.service.ChatService.process_query')
    def test_chat_query_success(self, mock_process, client, auth_headers, sample_chat_request):
        """測試聊天查詢成功"""
        # Mock 返回值
        mock_process.return_value = {
            "answer": "您可以透過以下方式申請農業補助...",
            "sources": [],
            "context_count": 3
        }
        
        response = client.post(
            "/api/v1/chat/query",
            json=sample_chat_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
    
    def test_chat_query_without_auth(self, client, sample_chat_request):
        """測試未認證的聊天查詢"""
        response = client.post("/api/v1/chat/query", json=sample_chat_request)
        
        assert response.status_code == 401
    
    def test_chat_query_empty_question(self, client, auth_headers):
        """測試空問題"""
        response = client.post(
            "/api/v1/chat/query",
            json={"question": ""},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # 驗證錯誤


class TestChatHistory:
    """測試聊天歷史"""
    
    @patch('src.domain.chat.service.ChatService.get_conversation_history')
    def test_get_history(self, mock_get_history, client, auth_headers):
        """測試取得聊天歷史"""
        # Mock 返回值
        mock_get_history.return_value = {
            "conversation_id": "test-conv-id",
            "messages": []
        }
        
        response = client.get(
            "/api/v1/chat/history/test-conv-id",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "messages" in data
