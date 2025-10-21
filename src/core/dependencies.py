# src/core/dependencies.py
"""
FastAPI 依賴注入
提供全域共用的依賴項
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from .security import decode_access_token


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    取得當前登入用戶
    
    從 JWT Token 中解析用戶 ID，並從資料庫查詢用戶資訊
    
    Args:
        token: JWT Token
        
    Returns:
        dict: 用戶資訊
        
    Raises:
        HTTPException: 當 Token 無效或用戶不存在時
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解碼 Token
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # 從資料庫查詢用戶
    from ..infrastructure.database.connection import DatabaseConnection
    from .config import Config
    
    db_conn = DatabaseConnection(Config)
    
    with db_conn.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, role, is_active FROM users WHERE id = %s",
                (user_id,)
            )
            user = cur.fetchone()
    
    if not user:
        raise credentials_exception
    
    # 檢查用戶是否啟用
    if not user[4]:  # is_active
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )
    
    return {
        "id": user[0],
        "username": user[1],
        "email": user[2],
        "role": user[3],
        "is_active": user[4]
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    取得當前啟用的用戶
    
    Args:
        current_user: 當前用戶
        
    Returns:
        dict: 用戶資訊
        
    Raises:
        HTTPException: 當用戶未啟用時
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號未啟用"
        )
    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    取得當前管理員用戶
    
    Args:
        current_user: 當前用戶
        
    Returns:
        dict: 管理員資訊
        
    Raises:
        HTTPException: 當用戶不是管理員時
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    return current_user


def get_db():
    """
    取得資料庫管理器實例
    
    Returns:
        PostgreSQLManager: 資料庫管理器
    """
    from ..infrastructure.database.connection import DatabaseConnection
    from .config import Config
    
    return DatabaseConnection(Config)


async def verify_websocket_token(token: str) -> dict:
    """
    驗證 WebSocket Token
    
    Args:
        token: JWT Token
        
    Returns:
        dict: 用戶資訊
        
    Raises:
        HTTPException: 當 Token 無效時
    """
    from .security import verify_websocket_token as verify_token
    
    try:
        return verify_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
