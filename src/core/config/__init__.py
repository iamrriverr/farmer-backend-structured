# src/core/config/__init__.py
"""
配置模組
統一匯出所有配置類別
"""

from .base import BaseConfig
from .llm import LLMConfig
from .prompts import PromptTemplates

__all__ = [
    "BaseConfig",
    "LLMConfig",
    "PromptTemplates",
    "Config"  # 向後相容
]


class Config(BaseConfig, LLMConfig):
    """
    統一配置類別（向後相容）
    繼承 BaseConfig 和 LLMConfig 的所有屬性
    """
    
    @classmethod
    def validate(cls):
        """驗證所有配置"""
        cls.init_directories()
        LLMConfig.validate()
        print("✅ 所有配置驗證通過")
    
    @classmethod
    def print_config(cls):
        """印出配置摘要"""
        print("\n" + "="*60)
        print("📋 系統配置")
        print("="*60)
        print(f"系統名稱: {cls.TITLE}")
        print(f"版本: {cls.VERSION}")
        print(f"主要 LLM: {cls.PRIMARY_LLM.upper()}")
        print(f"模型: {cls.GPT_MODEL if cls.PRIMARY_LLM == 'gpt' else cls.GEMINI_MODEL}")
        print(f"Embedding: {cls.OPENAI_EMBEDDING_MODEL}")
        print(f"資料庫: {cls.PG_HOST}:{cls.PG_PORT}/{cls.PG_DATABASE}")
        print(f"向量資料庫: {cls.CHROMA_PERSIST_DIR}")
        print(f"內網限制: {'啟用' if cls.INTERNAL_NETWORK_ONLY else '停用'}")
        print(f"日誌等級: {cls.LOG_LEVEL}")
        print("="*60 + "\n")
