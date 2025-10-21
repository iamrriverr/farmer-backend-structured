# src/core/config.py
"""
系統配置管理
統一管理所有環境變數和配置參數
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# 載入環境變數
load_dotenv()


class Config:
    """系統配置類別"""
    
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
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 小時
    
    # ============================================================
    # OpenAI API 設定
    # ============================================================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # ============================================================
    # Google AI 設定
    # ============================================================
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # ============================================================
    # LLM 選擇
    # ============================================================
    PRIMARY_LLM = os.getenv("PRIMARY_LLM", "gpt")  # "gpt" 或 "gemini"
    
    # ============================================================
    # PostgreSQL 資料庫設定
    # ============================================================
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DATABASE = os.getenv("PG_DATABASE", "farmer_rag")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD")
    
    if not PG_PASSWORD:
        raise ValueError("PG_PASSWORD 環境變數未設定")
    
    # ============================================================
    # Chroma 向量資料庫設定
    # ============================================================
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    
    CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "farmer_docs")
    
    # ============================================================
    # 檔案上傳設定
    # ============================================================
    UPLOAD_DIR = DATA_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc', '.md', '.csv', '.xlsx', '.xls'}
    
    # ============================================================
    # RAG 設定
    # ============================================================
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
    
    # ============================================================
    # 農會內網部署設定
    # ============================================================
    INTERNAL_NETWORK_ONLY = os.getenv("INTERNAL_NETWORK_ONLY", "false").lower() == "true"
    ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",") if os.getenv("ALLOWED_IPS") else []
    ALLOWED_NETWORKS = os.getenv("ALLOWED_NETWORKS", "192.168.0.0/16,10.0.0.0/8,172.16.0.0/12").split(",")
    
    # ============================================================
    # 日誌設定
    # ============================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = BASE_DIR / "logs"
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    
    # ============================================================
    # 資料保留策略
    # ============================================================
    CHAT_HISTORY_RETENTION_DAYS = int(os.getenv("CHAT_HISTORY_RETENTION_DAYS", "90"))
    DOCUMENT_RETENTION_DAYS = int(os.getenv("DOCUMENT_RETENTION_DAYS", "365"))
    
    # ============================================================
    # CORS 設定
    # ============================================================
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    
    @classmethod
    def validate(cls):
        """
        驗證必要的配置是否已設定
        
        Raises:
            ValueError: 當必要配置缺失時
        """
        required_configs = {
            "SECRET_KEY": cls.SECRET_KEY,
            "PG_PASSWORD": cls.PG_PASSWORD,
        }
        
        # 檢查 LLM API Key
        if cls.PRIMARY_LLM == "gpt" and not cls.OPENAI_API_KEY:
            raise ValueError("PRIMARY_LLM 設為 'gpt' 但 OPENAI_API_KEY 未設定")
        elif cls.PRIMARY_LLM == "gemini" and not cls.GOOGLE_API_KEY:
            raise ValueError("PRIMARY_LLM 設為 'gemini' 但 GOOGLE_API_KEY 未設定")
        
        # 檢查必要配置
        for name, value in required_configs.items():
            if not value:
                raise ValueError(f"{name} 環境變數未設定")
        
        # 確保目錄存在
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        print("✅ 配置驗證通過")
    
    @classmethod
    def get_model_name(cls) -> str:
        """
        取得當前使用的模型名稱
        
        Returns:
            str: 模型名稱
        """
        if cls.PRIMARY_LLM == "gpt":
            return cls.GPT_MODEL
        else:
            return cls.GEMINI_MODEL
    
    @classmethod
    def print_config(cls):
        """列印當前配置（隱藏敏感資訊）"""
        print("\n" + "=" * 60)
        print("📋 系統配置")
        print("=" * 60)
        print(f"系統名稱: {cls.TITLE}")
        print(f"版本: {cls.VERSION}")
        print(f"主要 LLM: {cls.PRIMARY_LLM.upper()}")
        print(f"模型: {cls.get_model_name()}")
        print(f"Embedding: {cls.EMBEDDING_MODEL}")
        print(f"資料庫: {cls.PG_HOST}:{cls.PG_PORT}/{cls.PG_DATABASE}")
        print(f"向量資料庫: {cls.CHROMA_PERSIST_DIR}")
        print(f"內網限制: {'啟用' if cls.INTERNAL_NETWORK_ONLY else '停用'}")
        print(f"日誌等級: {cls.LOG_LEVEL}")
        print("=" * 60 + "\n")
