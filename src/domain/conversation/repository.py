# src/domain/conversation/repository.py
"""
對話資料存取層 (Repository)
負責所有與對話相關的資料庫操作
"""

from typing import Optional, Dict, List
from psycopg2.extras import RealDictCursor
from datetime import datetime


class ConversationRepository:
    """對話資料存取類別"""
    
    def __init__(self, db_manager):
        """
        初始化 Repository
        
        Args:
            db_manager: PostgreSQLManager 實例
        """
        self.db = db_manager
    
    def create_conversation(self, user_id: int, title: str = "新對話") -> Dict:
        """
        建立新對話
        
        Args:
            user_id: 用戶 ID
            title: 對話標題
            
        Returns:
            Dict: 新建對話的資訊
        """
        sql = """
        INSERT INTO conversations (user_id, title, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        RETURNING id, user_id, title, message_count, is_pinned, is_archived,
                  last_message_at, created_at, updated_at
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id, title))
                result = cur.fetchone()
                conn.commit()
                return dict(result)
    
    def get_conversation_by_id(self, conversation_id: str, user_id: int) -> Optional[Dict]:
        """
        根據 ID 取得對話（驗證所有權）
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID
            
        Returns:
            Optional[Dict]: 對話資訊，不存在或無權限則返回 None
        """
        sql = """
        SELECT id, user_id, title, message_count, is_pinned, is_archived,
               last_message_at, created_at, updated_at
        FROM conversations
        WHERE id = %s AND user_id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (conversation_id, user_id))
                result = cur.fetchone()
                return dict(result) if result else None
    
    def get_user_conversations(self, user_id: int, include_archived: bool = False) -> List[Dict]:
        """
        取得用戶的所有對話列表
        
        Args:
            user_id: 用戶 ID
            include_archived: 是否包含已封存的對話
            
        Returns:
            List[Dict]: 對話列表
        """
        archive_filter = "" if include_archived else "AND is_archived = FALSE"
        
        sql = f"""
        SELECT id, title, message_count, is_pinned, is_archived,
               last_message_at, created_at, updated_at
        FROM conversations
        WHERE user_id = %s {archive_filter}
        ORDER BY is_pinned DESC, updated_at DESC
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                results = cur.fetchall()
                return [dict(row) for row in results]
    
    def update_conversation(self, conversation_id: str, **kwargs) -> Dict:
        """
        更新對話資訊
        
        Args:
            conversation_id: 對話 ID
            **kwargs: 要更新的欄位
            
        Returns:
            Dict: 更新後的對話資訊
        """
        allowed_fields = ['title', 'is_pinned', 'is_archived']
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            raise ValueError("沒有有效的更新欄位")
        
        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        sql = f"""
        UPDATE conversations
        SET {set_clause}, updated_at = NOW()
        WHERE id = %s
        RETURNING id, title, message_count, is_pinned, is_archived,
                  last_message_at, created_at, updated_at
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, list(update_fields.values()) + [conversation_id])
                result = cur.fetchone()
                conn.commit()
                return dict(result) if result else None
    
    def delete_conversation(self, conversation_id: str):
        """
        刪除對話（CASCADE 會自動刪除相關的聊天記錄）
        
        Args:
            conversation_id: 對話 ID
        """
        sql = "DELETE FROM conversations WHERE id = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (conversation_id,))
                conn.commit()
    
    def update_message_count(self, conversation_id: str, increment: int = 1):
        """
        更新對話的訊息數量
        
        Args:
            conversation_id: 對話 ID
            increment: 增加的數量
        """
        sql = """
        UPDATE conversations
        SET message_count = message_count + %s,
            last_message_at = NOW(),
            updated_at = NOW()
        WHERE id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (increment, conversation_id))
                conn.commit()
    
    def get_conversation_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        取得對話的聊天記錄
        
        Args:
            conversation_id: 對話 ID
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 訊息列表
        """
        sql = """
        SELECT message, created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at ASC
        LIMIT %s OFFSET %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (conversation_id, limit, offset))
                results = cur.fetchall()
                return [dict(row) for row in results]
    
    # src/domain/conversation/repository.py (僅修正 search_conversations 方法)

    def search_conversations(self, user_id: int, query: str) -> List[Dict]:
        """
        搜尋對話（標題 + 訊息內容）
        """
        sql = """
        SELECT DISTINCT
            c.id, c.title, c.message_count,
            c.last_message_at, c.created_at
        FROM conversations c
        LEFT JOIN chat_history ch ON c.id::text = ch.session_id
        WHERE c.user_id = %s
        AND (
            c.title ILIKE %s
            OR ch.message::text ILIKE %s
        )
        ORDER BY c.last_message_at DESC NULLS LAST
        LIMIT 50
        """
        
        search_pattern = f'%{query}%'
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id, search_pattern, search_pattern))
                results = cur.fetchall()
                return [dict(row) for row in results]

    
    def get_conversation_statistics(self, user_id: int) -> Dict:
        """
        取得用戶對話統計資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 統計資訊
        """
        sql = """
        SELECT
            COUNT(*) as total_conversations,
            COUNT(*) FILTER (WHERE is_archived = FALSE) as active_conversations,
            COUNT(*) FILTER (WHERE is_pinned = TRUE) as pinned_conversations,
            COALESCE(SUM(message_count), 0) as total_messages
        FROM conversations
        WHERE user_id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                result = cur.fetchone()
                
                return {
                    "total_conversations": result[0],
                    "active_conversations": result[1],
                    "pinned_conversations": result[2],
                    "total_messages": result[3]
                }
