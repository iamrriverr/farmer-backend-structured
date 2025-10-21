# src/domain/user/__init__.py
"""
用戶領域模組
包含用戶相關的 Schema、Repository、Service
"""

from .schemas import (
    UserRegister,
    UserLogin,
    Token,
    TokenData,
    UserResponse,
    UserUpdate,
    UserPreferences,
    PreferencesUpdate,
    UserStats,
    UserProfile,
    PasswordChange
)
from .repository import UserRepository
from .service import UserService

__all__ = [
    # Schemas
    "UserRegister",
    "UserLogin",
    "Token",
    "TokenData",
    "UserResponse",
    "UserUpdate",
    "UserPreferences",
    "PreferencesUpdate",
    "UserStats",
    "UserProfile",
    "PasswordChange",
    
    # Repository & Service
    "UserRepository",
    "UserService"
]
