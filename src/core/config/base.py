# src/core/config/base.py
"""
基礎配置
包含系統、資料庫、檔案、網路等基礎設定
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


class BaseConfig:
    """基礎系統配置"""
    
    # ============================================================
    # 系統基本設定
    # ============================================================
    TITLE = os.getenv("TITLE", "農會 RAG 系統")
    VERSION = os.getenv("VERSION", "2.0.0")
    DESCRIPTION = "農會智能客服與知識管理系統"
    
    # ============================================================
    # JWT 認證設定
    # ============================================================
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY 環境變數未設定")
    
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # ============================================================
    # PostgreSQL 設定
    # ============================================================
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DATABASE = os.getenv("PG_DATABASE", "farmer_rag")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "")
    
    # ============================================================
    # Chroma 向量資料庫設定
    # ============================================================
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    
    CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "farmer_documents")
    CHROMA_DISTANCE_FUNCTION = os.getenv("CHROMA_DISTANCE_FUNCTION", "cosine")
    
    # ============================================================
    # 檔案上傳設定
    # ============================================================
    UPLOAD_DIR = DATA_DIR / "uploads"
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
    ALLOWED_FILE_TYPES = [".pdf", ".docx", ".txt", ".xlsx", ".md"]
    
    # ============================================================
    # RAG 設定
    # ============================================================
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
    
    # ============================================================
    # 農會內網部署設定
    # ============================================================
    INTERNAL_NETWORK_ONLY = os.getenv("INTERNAL_NETWORK_ONLY", "false").lower() == "true"
    ALLOWED_IPS = os.getenv("ALLOWED_IPS", "127.0.0.1").split(",")
    ALLOWED_NETWORKS = os.getenv("ALLOWED_NETWORKS", "192.168.0.0/16,10.0.0.0/8,172.16.0.0/12").split(",")
    
    # ============================================================
    # 日誌設定
    # ============================================================
    LOG_DIR = BASE_DIR / "logs"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    
    # ============================================================
    # 資料保留策略
    # ============================================================
    CONVERSATION_RETENTION_DAYS = int(os.getenv("CONVERSATION_RETENTION_DAYS", "90"))
    DOCUMENT_RETENTION_DAYS = int(os.getenv("DOCUMENT_RETENTION_DAYS", "365"))
    
    @classmethod
    def init_directories(cls):
        """建立必要的目錄"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ 目錄已建立: {cls.DATA_DIR}, {cls.UPLOAD_DIR}, {cls.LOG_DIR}")
