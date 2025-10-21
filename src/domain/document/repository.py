# src/domain/document/repository.py
"""
文件資料存取層 (Repository)
負責所有與文件相關的資料庫操作
"""

from typing import Optional, Dict, List
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime


class DocumentRepository:
    """文件資料存取類別"""
    
    def __init__(self, db_manager):
        """
        初始化 Repository
        
        Args:
            db_manager: PostgreSQLManager 實例
        """
        self.db = db_manager
    
    def insert_document_metadata(self, user_id: int, filename: str, file_path: str,
                                file_size: int, file_type: str, content_hash: str,
                                department: Optional[str] = None,
                                job_type: Optional[str] = None,
                                year: Optional[int] = None,
                                document_type: str = "general") -> str:
        """
        插入文件 metadata
        
        Args:
            user_id: 用戶 ID
            filename: 檔案名稱
            file_path: 檔案路徑
            file_size: 檔案大小
            file_type: 檔案類型
            content_hash: 內容 hash
            department: 部門
            job_type: 工作類型
            year: 年份
            document_type: 文件類型
            
        Returns:
            str: 文件 ID
        """
        metadata = {
            "department": department,
            "job_type": job_type,
            "year": year,
            "document_type": document_type
        }
        
        sql = """
        INSERT INTO documents (
            user_id, filename, file_path, file_size, file_type,
            content_hash, metadata, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
        RETURNING id
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    user_id, filename, file_path, file_size, file_type,
                    content_hash, Json(metadata)
                ))
                doc_id = cur.fetchone()[0]
                conn.commit()
                return str(doc_id)
    
    def get_document_by_id(self, doc_id: str, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        根據 ID 取得文件
        
        Args:
            doc_id: 文件 ID
            user_id: 用戶 ID（用於權限驗證）
            
        Returns:
            Optional[Dict]: 文件資訊
        """
        sql = "SELECT * FROM documents WHERE id = %s"
        params = [doc_id]
        
        if user_id is not None:
            sql += " AND user_id = %s"
            params.append(user_id)
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                result = cur.fetchone()
                return dict(result) if result else None
    
    def get_user_documents(self, user_id: int, status: Optional[str] = None,
                          limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        取得用戶的文件列表
        
        Args:
            user_id: 用戶 ID
            status: 狀態過濾
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 文件列表
        """
        sql = "SELECT * FROM documents WHERE user_id = %s"
        params = [user_id]
        
        if status:
            sql += " AND status = %s"
            params.append(status)
        
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                results = cur.fetchall()
                return [dict(row) for row in results]
    
    def filter_documents(self, filters: Dict, user_id: int) -> List[Dict]:
        """
        根據多個條件過濾文件
        
        Args:
            filters: 過濾條件字典
            user_id: 用戶 ID
            
        Returns:
            List[Dict]: 文件列表
        """
        sql = "SELECT * FROM documents WHERE user_id = %s"
        params = [user_id]
        
        if filters.get("status"):
            sql += " AND status = %s"
            params.append(filters["status"])
        
        if filters.get("department"):
            sql += " AND metadata->>'department' = %s"
            params.append(filters["department"])
        
        if filters.get("year"):
            sql += " AND metadata->>'year' = %s"
            params.append(str(filters["year"]))
        
        sql += " ORDER BY created_at DESC"
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                results = cur.fetchall()
                return [dict(row) for row in results]
    
    def update_document_status(self, doc_id: str, status: str, 
                              error_message: Optional[str] = None):
        """
        更新文件狀態
        
        Args:
            doc_id: 文件 ID
            status: 新狀態 (pending/processing/completed/failed)
            error_message: 錯誤訊息（如果失敗）
        """
        if status == "completed":
            sql = """
            UPDATE documents
            SET status = %s, processed_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """
            params = (status, doc_id)
        else:
            sql = """
            UPDATE documents
            SET status = %s, error_message = %s, updated_at = NOW()
            WHERE id = %s
            """
            params = (status, error_message, doc_id)
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
    
    def update_chunk_count(self, doc_id: str, chunk_count: int):
        """
        更新文件的分塊數量
        
        Args:
            doc_id: 文件 ID
            chunk_count: 分塊數量
        """
        sql = """
        UPDATE documents
        SET chunk_count = %s, updated_at = NOW()
        WHERE id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (chunk_count, doc_id))
                conn.commit()
    
    def delete_document(self, doc_id: str):
        """
        刪除文件記錄
        
        Args:
            doc_id: 文件 ID
        """
        sql = "DELETE FROM documents WHERE id = %s"
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (doc_id,))
                conn.commit()
    
    def check_duplicate(self, user_id: int, content_hash: str) -> Optional[Dict]:
        """
        檢查是否存在重複文件
        
        Args:
            user_id: 用戶 ID
            content_hash: 內容 hash
            
        Returns:
            Optional[Dict]: 如果存在重複，返回文件資訊
        """
        sql = """
        SELECT id, filename FROM documents
        WHERE user_id = %s AND content_hash = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id, content_hash))
                result = cur.fetchone()
                return dict(result) if result else None
    
    def update_metadata(self, doc_id: str, metadata: Dict):
        """
        更新文件 metadata
        
        Args:
            doc_id: 文件 ID
            metadata: 新的 metadata
        """
        sql = """
        UPDATE documents
        SET metadata = %s, updated_at = NOW()
        WHERE id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (Json(metadata), doc_id))
                conn.commit()
    
    def get_document_statistics(self, user_id: int) -> Dict:
        """
        取得用戶文件統計資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 統計資訊
        """
        sql = """
        SELECT
            COUNT(*) as total_files,
            COALESCE(SUM(file_size), 0) as total_size,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
        FROM documents
        WHERE user_id = %s
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                result = cur.fetchone()
                
                return {
                    "total_files": result[0],
                    "total_size_bytes": result[1],
                    "total_size_mb": round(result[1] / 1024 / 1024, 2),
                    "status_distribution": {
                        "completed": result[2],
                        "processing": result[3],
                        "pending": result[4],
                        "failed": result[5]
                    }
                }
    
    def get_file_types_distribution(self, user_id: int) -> List[Dict]:
        """
        取得文件類型分布
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            List[Dict]: 文件類型統計
        """
        sql = """
        SELECT
            SUBSTRING(filename FROM '\\.([^.]+)$') as extension,
            COUNT(*) as count
        FROM documents
        WHERE user_id = %s
        GROUP BY extension
        ORDER BY count DESC
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                results = cur.fetchall()
                return [{"extension": row[0], "count": row[1]} for row in results]
