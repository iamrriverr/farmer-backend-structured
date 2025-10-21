# src/domain/user/repository.py
"""
用戶資料存取層 (Repository)
負責所有與用戶相關的資料庫操作
"""

from typing import Optional, Dict, List
from psycopg2.extras import RealDictCursor


class UserRepository:
    """用戶資料存取類別"""
    
    def __init__(self, db_manager):
        """
        初始化 Repository
        
        Args:
            db_manager: PostgreSQLManager 實例
        """
        self.db = db_manager
    
    def create_user(self, username: str, email: str, hashed_password: str, role: str = "user") -> Dict:
        """
        建立新用戶
        
        Args:
            username: 用戶名稱
            email: 電子郵件
            hashed_password: 加密後的密碼
            role: 用戶角色
            
        Returns:
            Dict: 新建用戶的資訊
        """
        sql = """
        INSERT INTO users (username, email, hashed_password, role, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id, username, email, role, created_at
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (username, email, hashed_password, role))
                result = cur.fetchone()
                conn.commit()
                return dict(result)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        根據 ID 取得用戶
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Optional[Dict]: 用戶資訊，不存在則返回 None
        """
        sql = "SELECT * FROM users WHERE id = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                result = cur.fetchone()
                return dict(result) if result else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        根據 Email 取得用戶
        
        Args:
            email: 電子郵件
            
        Returns:
            Optional[Dict]: 用戶資訊，不存在則返回 None
        """
        sql = "SELECT * FROM users WHERE email = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (email,))
                result = cur.fetchone()
                return dict(result) if result else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        根據用戶名取得用戶
        
        Args:
            username: 用戶名稱
            
        Returns:
            Optional[Dict]: 用戶資訊，不存在則返回 None
        """
        sql = "SELECT * FROM users WHERE username = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (username,))
                result = cur.fetchone()
                return dict(result) if result else None
    
    def update_user(self, user_id: int, **kwargs) -> Dict:
        """
        更新用戶資訊
        
        Args:
            user_id: 用戶 ID
            **kwargs: 要更新的欄位
            
        Returns:
            Dict: 更新後的用戶資訊
        """
        allowed_fields = ['username', 'email', 'hashed_password', 'role', 'is_active']
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            raise ValueError("沒有有效的更新欄位")
        
        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        sql = f"""
        UPDATE users 
        SET {set_clause}, updated_at = NOW() 
        WHERE id = %s
        RETURNING id, username, email, role, is_active, updated_at
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, list(update_fields.values()) + [user_id])
                result = cur.fetchone()
                conn.commit()
                return dict(result) if result else None
    
    def update_last_login(self, user_id: int):
        """
        更新用戶最後登入時間
        
        Args:
            user_id: 用戶 ID
        """
        sql = "UPDATE users SET last_login_at = NOW() WHERE id = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                conn.commit()
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        取得所有用戶列表（管理員功能）
        
        Args:
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 用戶列表
        """
        sql = """
        SELECT id, username, email, role, is_active, 
               last_login_at, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (limit, offset))
                results = cur.fetchall()
                return [dict(row) for row in results]
    
    def toggle_user_active(self, user_id: int) -> Dict:
        """
        切換用戶啟用狀態
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 更新後的用戶資訊
        """
        sql = """
        UPDATE users
        SET is_active = NOT is_active, updated_at = NOW()
        WHERE id = %s
        RETURNING id, username, is_active
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                result = cur.fetchone()
                conn.commit()
                return dict(result) if result else None
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """
        取得用戶統計資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 統計資訊
        """
        sql = """
        SELECT
            (SELECT COUNT(*) FROM conversations WHERE user_id = %s AND is_archived = FALSE) as active_conversations,
            (SELECT COUNT(*) FROM conversations WHERE user_id = %s) as total_conversations,
            (SELECT COUNT(*) FROM documents WHERE user_id = %s) as total_documents,
            (SELECT COALESCE(SUM(file_size), 0) FROM documents WHERE user_id = %s) as storage_used,
            (SELECT COALESCE(SUM(message_count), 0) FROM conversations WHERE user_id = %s) as total_messages,
            (SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE) as unread_notifications
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,) * 6)
                result = cur.fetchone()
                
                return {
                    "active_conversations": result[0],
                    "total_conversations": result[1],
                    "total_documents": result[2],
                    "storage_used_bytes": result[3],
                    "storage_used_mb": round(result[3] / 1024 / 1024, 2),
                    "total_messages": result[4],
                    "unread_notifications": result[5]
                }
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        取得用戶偏好設定
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 偏好設定字典
        """
        sql = """
        SELECT preference_key, preference_value, value_type
        FROM user_preferences
        WHERE user_id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                results = cur.fetchall()
                
                preferences = {}
                for row in results:
                    key, value, value_type = row
                    if value_type == "integer":
                        preferences[key] = int(value)
                    elif value_type == "boolean":
                        preferences[key] = value.lower() == "true"
                    elif value_type == "json":
                        import json
                        preferences[key] = json.loads(value)
                    else:
                        preferences[key] = value
                
                return preferences
    
    def update_user_preferences(self, user_id: int, preferences: Dict):
        """
        更新用戶偏好設定
        
        Args:
            user_id: 用戶 ID
            preferences: 偏好設定字典
        """
        sql = """
        INSERT INTO user_preferences (user_id, preference_key, preference_value, value_type)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, preference_key)
        DO UPDATE SET preference_value = EXCLUDED.preference_value,
                      value_type = EXCLUDED.value_type,
                      updated_at = NOW()
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                for key, value in preferences.items():
                    if isinstance(value, bool):
                        value_type = "boolean"
                        value_str = "true" if value else "false"
                    elif isinstance(value, int):
                        value_type = "integer"
                        value_str = str(value)
                    elif isinstance(value, dict) or isinstance(value, list):
                        value_type = "json"
                        import json
                        value_str = json.dumps(value)
                    else:
                        value_type = "string"
                        value_str = str(value)
                    
                    cur.execute(sql, (user_id, key, value_str, value_type))
                
                conn.commit()
    
    def create_default_preferences(self, user_id: int):
        """
        為新用戶建立預設偏好設定
        
        Args:
            user_id: 用戶 ID
        """
        default_preferences = [
            (user_id, "theme", "light", "string"),
            (user_id, "language", "zh-TW", "string"),
            (user_id, "rag_top_k", "5", "integer"),
            (user_id, "auto_save", "true", "boolean"),
        ]
        
        sql = """
        INSERT INTO user_preferences (user_id, preference_key, preference_value, value_type)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, preference_key) DO NOTHING
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, default_preferences)
                conn.commit()
