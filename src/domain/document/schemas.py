# src/domain/document/schemas.py
"""
文件領域相關的 Pydantic 模型定義
用於文件上傳、管理、查詢等數據驗證和序列化
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """文件上傳回應"""
    id: str
    filename: str
    file_path: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """文件資訊回應"""
    id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    chunk_count: int
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentDetail(BaseModel):
    """文件詳細資訊"""
    id: str
    filename: str
    file_path: str
    file_size: int
    file_type: str
    content_hash: Optional[str]
    status: str
    error_message: Optional[str]
    chunk_count: int
    vector_count: int
    embedding_model: str
    metadata: Dict[str, Any]
    preview: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentMetadataUpdate(BaseModel):
    """更新文件 metadata"""
    department: Optional[str] = Field(None, max_length=50, description="部門")
    job_type: Optional[str] = Field(None, max_length=50, description="工作類型")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="年份")
    document_type: Optional[str] = Field(None, max_length=50, description="文件類型")


class DocumentFilter(BaseModel):
    """文件過濾條件"""
    status: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None
    file_type: Optional[str] = None


class DocumentStats(BaseModel):
    """文件統計資訊"""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    status_distribution: Dict[str, int]
    file_types: list[Dict[str, Any]]
