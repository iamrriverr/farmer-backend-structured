# src/domain/document/service.py
"""
文件業務邏輯層 (Service)
處理文件相關的業務邏輯，協調 Repository、Processor 與外部服務
"""

from typing import Dict, Optional, List
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
import hashlib
import shutil
from datetime import datetime
from .repository import DocumentRepository
from .processor import DocumentProcessor
from .schemas import DocumentMetadataUpdate, DocumentFilter


class DocumentService:
    """文件業務邏輯類別"""
    
    # 支援的文件類型
    ALLOWED_EXTENSIONS = {
        '.pdf', '.txt', '.docx', '.doc', '.md',
        '.csv', '.xlsx', '.xls', '.json', '.xml'
    }
    
    def __init__(self, repository: DocumentRepository, processor: DocumentProcessor,
                 upload_dir: Path, max_file_size_mb: int = 50):
        """
        初始化 Service
        
        Args:
            repository: DocumentRepository 實例
            processor: DocumentProcessor 實例
            upload_dir: 上傳目錄
            max_file_size_mb: 最大檔案大小 (MB)
        """
        self.repo = repository
        self.processor = processor
        self.upload_dir = upload_dir
        self.max_file_size = max_file_size_mb * 1024 * 1024
    
    def validate_file(self, file: UploadFile) -> tuple[bool, str]:
        """
        驗證上傳的文件
        
        Args:
            file: 上傳的文件
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        # 檢查文件名
        if not file.filename:
            return False, "文件名不能為空"
        
        # 檢查文件擴展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"不支援的文件類型: {file_ext}。支援的類型: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        return True, ""
    
    def calculate_file_hash(self, file_path: str) -> str:
        """
        計算文件的 SHA-256 hash
        
        Args:
            file_path: 文件路徑
            
        Returns:
            str: hash 值
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def upload_document(self, file: UploadFile, user_id: int,
                       metadata: Optional[Dict] = None) -> Dict:
        """
        上傳文件
        
        Args:
            file: 上傳的文件
            user_id: 用戶 ID
            metadata: 文件 metadata
            
        Returns:
            Dict: 上傳結果
            
        Raises:
            HTTPException: 當驗證失敗或上傳失敗時
        """
        # 驗證文件
        is_valid, error_msg = self.validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 檢查文件大小
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小超過限制 ({self.max_file_size / 1024 / 1024}MB)"
            )
        
        try:
            # 確保上傳目錄存在
            user_upload_dir = self.upload_dir / str(user_id)
            user_upload_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file.filename}"
            file_path = user_upload_dir / safe_filename
            
            # 儲存文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 計算文件 hash
            content_hash = self.calculate_file_hash(str(file_path))
            
            # 檢查是否已存在相同文件
            existing = self.repo.check_duplicate(user_id, content_hash)
            if existing:
                file_path.unlink()  # 刪除重複文件
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"文件已存在: {existing['filename']}"
                )
            
            # 插入資料庫
            metadata = metadata or {}
            doc_id = self.repo.insert_document_metadata(
                user_id=user_id,
                filename=file.filename,
                file_path=str(file_path),
                file_size=file_size,
                file_type=file.content_type or "application/octet-stream",
                content_hash=content_hash,
                department=metadata.get("department"),
                job_type=metadata.get("job_type"),
                year=metadata.get("year"),
                document_type=metadata.get("document_type", "general")
            )
            
            return {
                "id": doc_id,
                "filename": file.filename,
                "file_path": str(file_path),
                "status": "pending",
                "created_at": datetime.now()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # 清理已上傳的文件
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"上傳失敗: {str(e)}"
            )
    
    def process_document(self, doc_id: str, vector_store_manager) -> int:
        """
        處理文件（載入、分塊、向量化）
        
        Args:
            doc_id: 文件 ID
            vector_store_manager: 向量儲存管理器
            
        Returns:
            int: 處理的分塊數量
            
        Raises:
            Exception: 當處理失敗時
        """
        # 更新狀態為處理中
        self.repo.update_document_status(doc_id, 'processing')
        
        try:
            # 取得文件資訊
            doc_info = self.repo.get_document_by_id(doc_id)
            if not doc_info:
                raise Exception("文件不存在")
            
            # 載入並分塊
            chunks = self.processor.load_and_split(doc_info['file_path'])
            if not chunks:
                raise Exception("文件處理失敗：無法載入或分塊")
            
            # 更新分塊數量
            self.repo.update_chunk_count(doc_id, len(chunks))
            
            # 向量化並存儲
            texts = [chunk.page_content for chunk in chunks]
            metadatas = [
                {
                    **chunk.metadata,
                    "document_id": doc_id,
                    "user_id": doc_info['user_id']
                }
                for chunk in chunks
            ]
            ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            
            vector_store_manager.add_documents(texts, metadatas, ids)
            
            # 更新為完成
            self.repo.update_document_status(doc_id, 'completed')
            
            return len(chunks)
            
        except Exception as e:
            self.repo.update_document_status(doc_id, 'failed', str(e))
            raise
    
    def delete_document(self, doc_id: str, user_id: int, 
                       delete_vectors: bool = True, vector_store_manager=None):
        """
        刪除文件
        
        Args:
            doc_id: 文件 ID
            user_id: 用戶 ID
            delete_vectors: 是否同時刪除向量資料
            vector_store_manager: 向量儲存管理器
        """
        # 查詢文件
        doc = self.repo.get_document_by_id(doc_id, user_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或無權限存取"
            )
        
        # 刪除實體文件
        file_path = Path(doc["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # 刪除向量資料
        if delete_vectors and vector_store_manager:
            try:
                vector_store_manager.delete_by_metadata({"document_id": doc_id})
            except Exception as e:
                print(f"⚠️ 刪除向量資料失敗: {e}")
        
        # 刪除資料庫記錄
        self.repo.delete_document(doc_id)
    
    def list_user_documents(self, user_id: int, filters: Optional[DocumentFilter] = None,
                           limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        查詢用戶文件列表
        
        Args:
            user_id: 用戶 ID
            filters: 過濾條件
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 文件列表
        """
        if filters:
            return self.repo.filter_documents(filters.dict(exclude_unset=True), user_id)
        else:
            return self.repo.get_user_documents(user_id, limit=limit, offset=offset)
    
    def get_document_detail(self, doc_id: str, user_id: int, 
                           vector_store_manager=None) -> Dict:
        """
        取得文件詳細資訊
        
        Args:
            doc_id: 文件 ID
            user_id: 用戶 ID
            vector_store_manager: 向量儲存管理器
            
        Returns:
            Dict: 文件詳細資訊
        """
        doc = self.repo.get_document_by_id(doc_id, user_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或無權限存取"
            )
        
        # 查詢向量統計
        vector_count = 0
        if vector_store_manager:
            try:
                results = vector_store_manager.search("", n_results=1, where={"document_id": doc_id})
                vector_count = len(results.get('ids', []))
            except:
                pass
        
        # 讀取文件內容預覽
        preview = self.processor.get_preview(doc["file_path"])
        
        return {
            **doc,
            "vector_count": vector_count,
            "preview": preview
        }
    
    def update_document_metadata(self, doc_id: str, user_id: int,
                                metadata_update: DocumentMetadataUpdate) -> Dict:
        """
        更新文件 metadata
        
        Args:
            doc_id: 文件 ID
            user_id: 用戶 ID
            metadata_update: 更新資料
            
        Returns:
            Dict: 更新結果
        """
        # 驗證文件所有權
        doc = self.repo.get_document_by_id(doc_id, user_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或無權限存取"
            )
        
        # 更新 metadata
        metadata = doc.get("metadata", {})
        update_dict = metadata_update.dict(exclude_unset=True)
        metadata.update(update_dict)
        
        self.repo.update_metadata(doc_id, metadata)
        
        return {
            "message": "Metadata 已更新",
            "document_id": doc_id,
            "metadata": metadata
        }
    
    def get_document_statistics(self, user_id: int) -> Dict:
        """
        取得文件統計資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 統計資訊
        """
        stats = self.repo.get_document_statistics(user_id)
        file_types = self.repo.get_file_types_distribution(user_id)
        
        return {
            **stats,
            "file_types": file_types
        }
