# src/domain/chat/repository.py
"""
聊天資料存取層 (Repository)
負責所有與聊天記錄相關的資料庫操作

完全匹配 schema.sql 的 JSONB 格式設計：
- chat_history 表使用 session_id (TEXT) 和 message (JSONB)
- 相容 LangChain 的 PostgresChatMessageHistory 格式
"""

from typing import Optional, Dict, List, Tuple
from psycopg2.extras import RealDictCursor, Json
import json


class ChatRepository:
    """聊天資料存取類別"""
    
    def __init__(self, db_manager):
        """
        初始化 Repository
        
        Args:
            db_manager: PostgreSQLManager 實例
        """
        self.db = db_manager
    
    def save_message(self, conversation_id: str, role: str, content: str,
                    sources: Optional[List[Dict]] = None,
                    intent: Optional[Dict] = None):
        """
        儲存聊天訊息（使用 JSONB 格式）
        
        Args:
            conversation_id: 對話 ID (對應 session_id)
            role: 角色（user/assistant）
            content: 訊息內容
            sources: 來源文件列表
            intent: 意圖分類結果
        
        Note:
            - 使用 LangChain 相容的 message 格式
            - conversation_id 會自動轉為 TEXT 類型儲存到 session_id
            - 整個訊息結構儲存為 JSONB
        """
        # 建立 LangChain 相容的訊息格式
        message_data = {
            "type": "human" if role == "user" else "ai",
            "content": content,
            "data": {
                "sources": sources or [],
                "intent": intent or {},
                "role": role  # 保留原始 role 方便查詢
            }
        }
        
        sql = """
        INSERT INTO chat_history (session_id, message, created_at)
        VALUES (%s, %s, NOW())
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    conversation_id,  # UUID -> TEXT 自動轉換
                    Json(message_data)  # Dict -> JSONB
                ))
                conn.commit()
    
    def get_chat_history(self, conversation_id: str, limit: int = 100,
                        offset: int = 0) -> List[Dict]:
        """
        取得聊天記錄（解析 JSONB）
        
        Args:
            conversation_id: 對話 ID
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 聊天記錄列表，每筆包含：
                - role: 角色
                - content: 內容
                - sources: 來源文件
                - intent: 意圖分類
                - created_at: 建立時間
        """
        sql = """
        SELECT 
            message->'data'->>'role' as role,
            message->>'content' as content,
            message->'data'->'sources' as sources,
            message->'data'->'intent' as intent,
            created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at ASC
        LIMIT %s OFFSET %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (conversation_id, limit, offset))
                results = cur.fetchall()
                
                # 處理 JSONB 欄位（sources 和 intent）
                processed_results = []
                for row in results:
                    row_dict = dict(row)
                    
                    # 將 JSONB 字串轉為 Python 物件
                    if row_dict.get('sources'):
                        row_dict['sources'] = json.loads(row_dict['sources']) if isinstance(row_dict['sources'], str) else row_dict['sources']
                    else:
                        row_dict['sources'] = []
                    
                    if row_dict.get('intent'):
                        row_dict['intent'] = json.loads(row_dict['intent']) if isinstance(row_dict['intent'], str) else row_dict['intent']
                    else:
                        row_dict['intent'] = {}
                    
                    processed_results.append(row_dict)
                
                return processed_results
    
    def get_recent_history(self, conversation_id: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        取得最近的對話歷史（用於提供上下文給 LLM）
        
        Args:
            conversation_id: 對話 ID
            limit: 返回數量限制
            
        Returns:
            List[Tuple[str, str]]: (role, content) 元組列表
        """
        sql = """
        SELECT 
            message->'data'->>'role' as role,
            message->>'content' as content
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (conversation_id, limit))
                results = cur.fetchall()
                
                # 反轉順序（最舊的在前）
                return [(row[0], row[1]) for row in reversed(results)]
    
    def clear_chat_history(self, conversation_id: str):
        """
        清空對話歷史
        
        Args:
            conversation_id: 對話 ID
        """
        sql = "DELETE FROM chat_history WHERE session_id = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (conversation_id,))
                conn.commit()
    
    def get_message_count(self, conversation_id: str) -> int:
        """
        取得對話的訊息數量
        
        Args:
            conversation_id: 對話 ID
            
        Returns:
            int: 訊息數量
        """
        sql = "SELECT COUNT(*) FROM chat_history WHERE session_id = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (conversation_id,))
                result = cur.fetchone()
                return result[0] if result else 0
    
    def update_conversation_stats(self, conversation_id: str, user_id: int, 
                                  message_increment: int = 2):
        """
        更新對話統計資訊（訊息數、最後訊息時間）
        
        Args:
            conversation_id: 對話 ID
            user_id: 用戶 ID（用於驗證所有權）
            message_increment: 訊息增量（預設2，一問一答）
        
        Note:
            這個方法通常在觸發器中自動執行，手動調用時要小心
        """
        sql = """
        UPDATE conversations
        SET message_count = message_count + %s,
            last_message_at = NOW(),
            updated_at = NOW()
        WHERE id::text = %s AND user_id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (message_increment, conversation_id, user_id))
                conn.commit()
    
    def search_messages(self, conversation_id: str, query: str, 
                       limit: int = 50) -> List[Dict]:
        """
        在對話中搜尋訊息
        
        Args:
            conversation_id: 對話 ID
            query: 搜尋關鍵字
            limit: 返回數量限制
            
        Returns:
            List[Dict]: 符合的訊息列表
        """
        sql = """
        SELECT 
            message->'data'->>'role' as role,
            message->>'content' as content,
            created_at
        FROM chat_history
        WHERE session_id = %s
          AND message->>'content' ILIKE %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (conversation_id, f'%{query}%', limit))
                results = cur.fetchall()
                return [dict(row) for row in results]
    
    def get_latest_message(self, conversation_id: str) -> Optional[Dict]:
        """
        取得對話的最新訊息
        
        Args:
            conversation_id: 對話 ID
            
        Returns:
            Optional[Dict]: 最新訊息，不存在則返回 None
        """
        sql = """
        SELECT 
            message->'data'->>'role' as role,
            message->>'content' as content,
            created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (conversation_id,))
                result = cur.fetchone()
                return dict(result) if result else None
