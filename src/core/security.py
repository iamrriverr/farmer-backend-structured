# src/core/security.py
"""
安全模組
提供密碼加密、JWT Token 生成與驗證等功能
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


# 使用 Argon2 密碼加密（比 bcrypt 更安全且無長度限制）
pwd_hasher = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼
    
    Args:
        plain_password: 明文密碼
        hashed_password: 加密後的密碼
        
    Returns:
        bool: 是否匹配
    """
    try:
        pwd_hasher.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False
    except Exception as e:
        print(f"❌ 密碼驗證錯誤: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    加密密碼
    
    Args:
        password: 明文密碼
        
    Returns:
        str: 加密後的密碼
    """
    return pwd_hasher.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成 JWT Access Token
    
    Args:
        data: 要編碼的數據（通常包含 user_id）
        expires_delta: 過期時間差
        
    Returns:
        str: JWT Token
    """
    from .config import Config
    
    to_encode = data.copy()
    
    # 設定過期時間
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # 生成 JWT
    encoded_jwt = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解碼 JWT Access Token
    
    Args:
        token: JWT Token
        
    Returns:
        Optional[dict]: 解碼後的數據，失敗返回 None
    """
    from .config import Config
    
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.ALGORITHM]
        )
        return payload
    except JWTError as e:
        print(f"❌ Token 解碼失敗: {e}")
        return None


def verify_websocket_token(token: str) -> dict:
    """
    驗證 WebSocket 連線的 Token
    
    Args:
        token: JWT Token
        
    Returns:
        dict: 用戶資訊
        
    Raises:
        Exception: 當 Token 無效時
    """
    payload = decode_access_token(token)
    if not payload:
        raise Exception("無效的 Token")
    
    user_id = payload.get("user_id")
    if not user_id:
        raise Exception("Token 中缺少 user_id")
    
    # 返回簡化的用戶資訊（WebSocket 不需要完整資料）
    return {"id": user_id}
