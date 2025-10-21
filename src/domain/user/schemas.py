# src/domain/user/schemas.py
"""
用戶領域相關的 Pydantic 模型定義
用於用戶註冊、登入、認證、資訊回應等數據驗證和序列化
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


# ============================================================
# 認證相關模型
# ============================================================

class UserRegister(BaseModel):
    """用戶註冊請求"""
    username: str = Field(..., min_length=3, max_length=50, description="用戶名稱")
    email: EmailStr = Field(..., description="電子郵件")
    password: str = Field(..., min_length=6, description="密碼（至少6字元）")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """驗證用戶名只包含字母、數字和底線"""
        if not v.replace('_', '').isalnum():
            raise ValueError('用戶名只能包含字母、數字和底線')
        return v


class UserLogin(BaseModel):
    """用戶登入請求"""
    email: EmailStr = Field(..., description="電子郵件")
    password: str = Field(..., description="密碼")


class Token(BaseModel):
    """JWT Token 回應"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 解碼後的數據"""
    user_id: Optional[int] = None


class UserResponse(BaseModel):
    """用戶資訊回應"""
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用戶更新請求"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用戶名稱")
    email: Optional[EmailStr] = Field(None, description="電子郵件")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """驗證用戶名只包含字母、數字和底線"""
        if v and not v.replace('_', '').isalnum():
            raise ValueError('用戶名只能包含字母、數字和底線')
        return v


# ============================================================
# 用戶偏好設定相關模型
# ============================================================

class UserPreferences(BaseModel):
    """用戶偏好設定"""
    theme: Optional[str] = "light"
    language: Optional[str] = "zh-TW"
    rag_top_k: Optional[int] = 5
    auto_save: Optional[bool] = True


class PreferencesUpdate(BaseModel):
    """更新偏好設定"""
    preferences: Dict[str, Any]


# ============================================================
# 用戶統計相關模型
# ============================================================

class UserStats(BaseModel):
    """用戶統計資訊"""
    user_id: int
    stats: Dict[str, Any]


class UserProfile(BaseModel):
    """用戶完整資料（含統計）"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    # 統計資訊
    active_conversations: int = 0
    total_conversations: int = 0
    total_documents: int = 0
    storage_used: int = 0
    
    # 偏好設定
    preferences: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


# ============================================================
# 密碼相關模型
# ============================================================

class PasswordChange(BaseModel):
    """修改密碼請求"""
    old_password: str = Field(..., min_length=6, description="舊密碼")
    new_password: str = Field(..., min_length=6, description="新密碼")
    
    @validator('new_password')
    def passwords_different(cls, v, values):
        """驗證新舊密碼不同"""
        if 'old_password' in values and v == values['old_password']:
            raise ValueError('新密碼不能與舊密碼相同')
        return v
