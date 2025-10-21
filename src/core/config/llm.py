# src/core/config/llm.py
"""
LLM 配置
包含 OpenAI、Google Gemini 等 LLM 相關設定
"""

import os
from dotenv import load_dotenv

load_dotenv()


class LLMConfig:
    """LLM 模型配置"""
    
    # ============================================================
    # OpenAI API 設定
    # ============================================================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # ============================================================
    # Google Gemini API 設定
    # ============================================================
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # ============================================================
    # LLM 選擇
    # ============================================================
    PRIMARY_LLM = os.getenv("PRIMARY_LLM", "gpt").lower()  # gpt 或 gemini
    
    # ============================================================
    # LLM 生成參數
    # ============================================================
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))  # 0.0-1.0，數值越低越保守
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
    TOP_P = float(os.getenv("TOP_P", "0.9"))
    FREQUENCY_PENALTY = float(os.getenv("FREQUENCY_PENALTY", "0.0"))
    PRESENCE_PENALTY = float(os.getenv("PRESENCE_PENALTY", "0.0"))
    
    # ============================================================
    # 串流設定
    # ============================================================
    ENABLE_STREAMING = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    STREAM_CHUNK_SIZE = int(os.getenv("STREAM_CHUNK_SIZE", "1024"))
    
    @classmethod
    def validate(cls):
        """驗證 LLM 配置"""
        errors = []
        
        # 檢查主要 LLM 設定
        if cls.PRIMARY_LLM not in ["gpt", "gemini"]:
            errors.append("PRIMARY_LLM 必須是 'gpt' 或 'gemini'")
        
        # 檢查對應的 API Key
        if cls.PRIMARY_LLM == "gpt" and not cls.OPENAI_API_KEY:
            errors.append("PRIMARY_LLM 設為 'gpt' 但 OPENAI_API_KEY 未設定")
        
        if cls.PRIMARY_LLM == "gemini" and not cls.GOOGLE_API_KEY:
            errors.append("PRIMARY_LLM 設為 'gemini' 但 GOOGLE_API_KEY 未設定")
        
        # 檢查參數範圍
        if not 0.0 <= cls.TEMPERATURE <= 1.0:
            errors.append("TEMPERATURE 必須介於 0.0 和 1.0 之間")
        
        if not 0.0 <= cls.TOP_P <= 1.0:
            errors.append("TOP_P 必須介於 0.0 和 1.0 之間")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True
    
    @classmethod
    def get_model_info(cls) -> dict:
        """取得當前模型資訊"""
        return {
            "primary_llm": cls.PRIMARY_LLM,
            "model": cls.GPT_MODEL if cls.PRIMARY_LLM == "gpt" else cls.GEMINI_MODEL,
            "embedding": cls.OPENAI_EMBEDDING_MODEL,
            "temperature": cls.TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS
        }
