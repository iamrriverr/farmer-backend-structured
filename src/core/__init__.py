# src/core/__init__.py
"""
核心模組
匯出所有核心功能
"""

from .config import Config
from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    verify_websocket_token
)
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_db
)
from .exceptions import (
    BusinessException,
    ResourceNotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    DuplicateResourceException,
    ServiceUnavailableException
)

__all__ = [
    # Config
    "Config",
    
    # Security
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "verify_websocket_token",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_db",
    
    # Exceptions
    "BusinessException",
    "ResourceNotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
    "DuplicateResourceException",
    "ServiceUnavailableException"
]
