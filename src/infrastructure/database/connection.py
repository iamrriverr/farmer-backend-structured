# src/infrastructure/database/connection.py
"""
資料庫連線管理
負責 PostgreSQL 連線池的初始化與管理
"""

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Optional


class DatabaseConnection:
    """資料庫連線管理類別"""
    
    def __init__(self, config):
        """
        初始化資料庫連線
        
        Args:
            config: 配置物件
        """
        self.config = config
        self.pool: Optional[SimpleConnectionPool] = None
        self.init_pool()
    
    def init_pool(self):
        """初始化連線池"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.config.PG_HOST,
                port=self.config.PG_PORT,
                database=self.config.PG_DATABASE,
                user=self.config.PG_USER,
                password=self.config.PG_PASSWORD
            )
            print("✅ PostgreSQL 連線池已建立")
        except Exception as e:
            print(f"❌ PostgreSQL 連線失敗: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        取得資料庫連線的上下文管理器
        
        Yields:
            connection: 資料庫連線物件
        """
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def close_pool(self):
        """關閉連線池"""
        if self.pool:
            self.pool.closeall()
            print("✅ PostgreSQL 連線池已關閉")
    
    def test_connection(self) -> bool:
        """
        測試資料庫連線
        
        Returns:
            bool: 連線是否成功
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result[0] == 1
        except Exception as e:
            print(f"❌ 資料庫連線測試失敗: {e}")
            return False
