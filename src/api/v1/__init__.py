# src/api/v1/__init__.py
"""
API v1 路由模組
包含所有版本 1 的 API 端點
"""

from .auth import router as auth_router
from .users import router as users_router
from .conversations import router as conversations_router
from .documents import router as documents_router
from .chat import router as chat_router

# 匯出所有路由
__all__ = [
    "auth_router",
    "users_router", 
    "conversations_router",
    "documents_router",
    "chat_router",
    "register_all_routers"
]


def register_all_routers(app, prefix: str = "/api/v1"):
    """
    將所有 v1 路由註冊到 FastAPI 應用
    
    Args:
        app: FastAPI 應用實例
        prefix: 路由前綴（預設 /api/v1）
        
    Example:
        >>> from fastapi import FastAPI
        >>> from src.api.v1 import register_all_routers
        >>> 
        >>> app = FastAPI()
        >>> register_all_routers(app)
    """
    routers = [
        (auth_router, "認證"),
        (users_router, "用戶管理"),
        (conversations_router, "對話管理"),
        (documents_router, "文件管理"),
        (chat_router, "聊天")
    ]
    
    for router, name in routers:
        app.include_router(router, prefix=prefix)
        print(f"  ✓ {name}")
    
    print(f"✅ 已註冊 {len(routers)} 個 API v1 路由")
