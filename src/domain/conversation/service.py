# src/domain/conversation/service.py
"""
對話業務邏輯層 (Service)
處理對話相關的業務邏輯，協調 Repository 與外部服務
"""

from typing import Dict, Optional, List
from fastapi import HTTPException, status
from .repository import ConversationRepository
from .schemas import ConversationCreate, ConversationUpdate, ConversationFilter


class ConversationService:
    """對話業務邏輯類別"""
    
    def __init__(self, repository: ConversationRepository):
        """
        初始化 Service
        
        Args:
            repository: ConversationRepository 實例
        """
        self.repo = repository
    
    def create_conversation(self, user_id: int, title: Optional[str] = None) -> Dict:
        """
        建立新對話
        
        Args:
            user_id: 用戶 ID
            title: 對話標題
            
        Returns:
            Dict: 新建對話資訊
        """
        conversation_title = title or "新對話"
        conversation = self.repo.create_conversation(user_id, conversation_title)
        
        return {
            "id": str(conversation["id"]),
            "title": conversation["title"],
            "created_at": conversation["created_at"].isoformat()
        }
    
    def get_conversation_detail(self, conversation_id: str, user_id: int) -> Dict:
        """
        取得對話詳細資訊
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            
        Returns:
            Dict: 對話詳細資訊
            
        Raises:
            HTTPException: 當對話不存在或無權限時
        """
        conversation = self.repo.get_conversation_by_id(conversation_id, user_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在或無權限存取"
            )
        
        return {
            "id": str(conversation["id"]),
            "title": conversation["title"],
            "message_count": conversation["message_count"],
            "is_pinned": conversation["is_pinned"],
            "is_archived": conversation["is_archived"],
            "last_message_at": conversation["last_message_at"].isoformat() if conversation["last_message_at"] else None,
            "created_at": conversation["created_at"].isoformat(),
            "updated_at": conversation["updated_at"].isoformat()
        }
    
    def list_user_conversations(self, user_id: int, filters: Optional[ConversationFilter] = None) -> List[Dict]:
        """
        查詢用戶對話列表
        
        Args:
            user_id: 用戶 ID
            filters: 過濾條件
            
        Returns:
            List[Dict]: 對話列表
        """
        include_archived = filters.include_archived if filters else False
        conversations = self.repo.get_user_conversations(user_id, include_archived)
        
        # 應用額外的過濾條件
        if filters and filters.is_pinned is not None:
            conversations = [c for c in conversations if c["is_pinned"] == filters.is_pinned]
        
        if filters and filters.date_from:
            conversations = [c for c in conversations if c["created_at"] >= filters.date_from]
        
        if filters and filters.date_to:
            conversations = [c for c in conversations if c["created_at"] <= filters.date_to]
        
        return conversations
    
    def update_conversation_title(self, conversation_id: str, user_id: int, title: str) -> Dict:
        """
        更新對話標題
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            title: 新標題
            
        Returns:
            Dict: 更新結果
            
        Raises:
            HTTPException: 當對話不存在或無權限時
        """
        # 驗證所有權
        conversation = self.repo.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在或無權限存取"
            )
        
        updated = self.repo.update_conversation(conversation_id, title=title)
        
        return {
            "message": "對話標題已更新",
            "conversation_id": conversation_id,
            "title": updated["title"]
        }
    
    def toggle_pin(self, conversation_id: str, user_id: int) -> Dict:
        """
        切換對話置頂狀態
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            
        Returns:
            Dict: 更新結果
        """
        conversation = self.repo.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在或無權限存取"
            )
        
        new_pinned_status = not conversation["is_pinned"]
        updated = self.repo.update_conversation(conversation_id, is_pinned=new_pinned_status)
        
        return {
            "message": "置頂" if new_pinned_status else "取消置頂",
            "conversation_id": conversation_id,
            "is_pinned": updated["is_pinned"]
        }
    
    def toggle_archive(self, conversation_id: str, user_id: int) -> Dict:
        """
        切換對話封存狀態
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            
        Returns:
            Dict: 更新結果
        """
        conversation = self.repo.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在或無權限存取"
            )
        
        new_archived_status = not conversation["is_archived"]
        updated = self.repo.update_conversation(conversation_id, is_archived=new_archived_status)
        
        return {
            "message": "已封存" if new_archived_status else "已取消封存",
            "conversation_id": conversation_id,
            "is_archived": updated["is_archived"]
        }
    
    def delete_conversation(self, conversation_id: str, user_id: int):
        """
        刪除對話
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            
        Raises:
            HTTPException: 當對話不存在或無權限時
        """
        # 驗證所有權
        conversation = self.repo.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在或無權限存取"
            )
        
        self.repo.delete_conversation(conversation_id)
    
    def search_conversations(self, user_id: int, query: str) -> Dict:
        """
        搜尋對話
        
        Args:
            user_id: 用戶 ID
            query: 搜尋關鍵字
            
        Returns:
            Dict: 搜尋結果
        """
        if not query or len(query.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="搜尋關鍵字不能為空"
            )
        
        results = self.repo.search_conversations(user_id, query.strip())
        
        return {
            "query": query,
            "results": [
                {
                    "id": str(row["id"]),
                    "title": row["title"],
                    "message_count": row["message_count"],
                    "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
                    "created_at": row["created_at"].isoformat()
                }
                for row in results
            ],
            "total": len(results)
        }
    
    def get_conversation_messages(self, conversation_id: str, user_id: int, 
                                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        取得對話的聊天記錄
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 訊息列表
        """
        # 驗證所有權
        conversation = self.repo.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在或無權限存取"
            )
        
        messages = self.repo.get_conversation_messages(conversation_id, limit, offset)
        
        # 解析 JSONB message 欄位
        formatted_messages = []
        for row in messages:
            msg_data = row["message"]
            formatted_messages.append({
                "role": msg_data.get("type", "human"),
                "content": msg_data.get("content", ""),
                "timestamp": row["created_at"].isoformat()
            })
        
        return formatted_messages
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """
        取得用戶對話統計資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 統計資訊
        """
        return self.repo.get_conversation_statistics(user_id)
