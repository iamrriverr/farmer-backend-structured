# src/domain/document/__init__.py
"""
文件領域模組
包含文件相關的 Schema、Repository、Service、Processor
"""

from .schemas import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentDetail,
    DocumentMetadataUpdate,
    DocumentFilter,
    DocumentStats
)
from .repository import DocumentRepository
from .service import DocumentService
from .processor import DocumentProcessor

__all__ = [
    # Schemas
    "DocumentUploadResponse",
    "DocumentResponse",
    "DocumentDetail",
    "DocumentMetadataUpdate",
    "DocumentFilter",
    "DocumentStats",
    
    # Repository, Service & Processor
    "DocumentRepository",
    "DocumentService",
    "DocumentProcessor"
]
