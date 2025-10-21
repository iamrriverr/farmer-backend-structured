# src/api/middleware/__init__.py
"""
中介層模組
包含錯誤處理、日誌記錄、IP 白名單等中介層
"""

from .error_handler import (
    setup_exception_handlers,
    BusinessException,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    business_exception_handler
)
from .logging import (
    setup_logging_middleware,
    DetailedRequestLogger,
    logger,
    RequestLoggingMiddleware
)
from .ip_whitelist import (
    setup_ip_whitelist_middleware,
    is_internal_ip,
    IPWhitelistMiddleware
)

__all__ = [
    # 錯誤處理
    "setup_exception_handlers",
    "BusinessException",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
    "business_exception_handler",
    
    # 日誌
    "setup_logging_middleware", 
    "DetailedRequestLogger",
    "logger",
    "RequestLoggingMiddleware",
    
    # IP 白名單
    "setup_ip_whitelist_middleware",
    "is_internal_ip",
    "IPWhitelistMiddleware",
    
    # 統一設定
    "setup_all_middleware"
]


def setup_all_middleware(app, config):
    """
    一次性設定所有中介層
    
    執行順序（重要）：
    1. IP 白名單（最先檢查）
    2. 日誌記錄
    3. 錯誤處理（最後捕獲）
    
    Args:
        app: FastAPI 應用實例
        config: 配置物件（src.core.config.Config）
        
    Example:
        >>> from fastapi import FastAPI
        >>> from src.core.config import Config
        >>> from src.api.middleware import setup_all_middleware
        >>> 
        >>> app = FastAPI()
        >>> setup_all_middleware(app, Config)
    """
    print("\n⚙️  設定中介層...")
    
    # 1. IP 白名單
    setup_ip_whitelist_middleware(app, config)
    
    # 2. 日誌記錄
    setup_logging_middleware(app)
    
    # 3. 錯誤處理
    setup_exception_handlers(app)
    
    print("✅ 所有中介層設定完成\n")
