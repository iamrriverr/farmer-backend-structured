# src/api/v1/documents.py
"""
文件管理 API 路由
處理文件上傳、查詢、刪除等
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from typing import List, Dict, Optional

from ...domain.document.schemas import (
    DocumentUploadResponse, DocumentResponse, DocumentFilter, DocumentMetadataUpdate
)
from ...domain.document.service import DocumentService
from ...domain.document.repository import DocumentRepository
from ...domain.document.processor import DocumentProcessor
from ...infrastructure.vector_store import VectorStoreManager
from ...core.dependencies import get_current_user, get_db
from ...core.config import Config

router = APIRouter(prefix="/documents", tags=["文件管理"])

#這邊設計只允許管理員上傳文件
def check_admin_role(current_user = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="只有管理員可以上傳文件")
    return current_user



def get_document_service(db=Depends(get_db)) -> DocumentService:
    """依賴注入：取得 DocumentService"""
    repo = DocumentRepository(db)
    processor = DocumentProcessor(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP
    )
    return DocumentService(
        repository=repo,
        processor=processor,
        upload_dir=Config.UPLOAD_DIR,
        max_file_size_mb=50
    )


def get_vector_store() -> VectorStoreManager:
    """依賴注入：取得 VectorStoreManager"""
    return VectorStoreManager(Config)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    department: Optional[str] = Query(None, description="部門"),
    job_type: Optional[str] = Query(None, description="工作類型"),
    year: Optional[int] = Query(None, description="年份"),
    document_type: str = Query("general", description="文件類型"),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(check_admin_role),
    vector_store: VectorStoreManager = Depends(get_vector_store)
):
    """
    上傳文件
    
    支援格式：PDF, DOCX, TXT, MD, CSV, XLSX 等
    """
    # 準備 metadata
    metadata = {
        "department": department,
        "job_type": job_type,
        "year": year,
        "document_type": document_type
    }
    
    # 上傳文件
    result = document_service.upload_document(
        file=file,
        user_id=current_user["id"],
        metadata=metadata
    )
    
    # 背景處理文件（向量化）
    if background_tasks:
        background_tasks.add_task(
            document_service.process_document,
            result["id"],
            vector_store
        )
    
    return DocumentUploadResponse(**result)


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    status: Optional[str] = Query(None, description="狀態過濾"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    查詢用戶的文件列表
    """
    filters = DocumentFilter(status=status) if status else None
    documents = document_service.list_user_documents(
        current_user["id"],
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    return documents


@router.get("/{doc_id}", response_model=Dict)
async def get_document_detail(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    vector_store: VectorStoreManager = Depends(get_vector_store)
):
    """
    查詢文件詳細資訊
    """
    document = document_service.get_document_detail(
        doc_id,
        current_user["id"],
        vector_store
    )
    
    return document


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    vector_store: VectorStoreManager = Depends(get_vector_store)
):
    """
    刪除文件
    
    同時刪除實體檔案和向量資料
    """
    document_service.delete_document(
        doc_id,
        current_user["id"],
        delete_vectors=True,
        vector_store_manager=vector_store
    )


@router.get("/statistics/summary", response_model=Dict)
async def get_document_statistics(
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    取得文件統計資訊
    """
    stats = document_service.get_document_statistics(current_user["id"])
    return stats


@router.post("/filter", response_model=List[Dict])
async def filter_documents(
    filters: DocumentFilter,
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    根據多個條件過濾文件
    """
    documents = document_service.list_user_documents(
        current_user["id"],
        filters=filters
    )
    
    return documents


@router.patch("/{doc_id}/metadata")
async def update_document_metadata(
    doc_id: str,
    metadata_update: DocumentMetadataUpdate,
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    更新文件 metadata
    """
    result = document_service.update_document_metadata(
        doc_id,
        current_user["id"],
        metadata_update
    )
    
    return result
