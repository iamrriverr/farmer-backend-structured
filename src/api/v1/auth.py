# src/api/v1/auth.py
"""
認證 API 路由
處理用戶註冊、登入、Token 驗證等
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict
from datetime import timedelta

from ...domain.user.schemas import UserRegister, UserLogin, Token, UserResponse
from ...domain.user.service import UserService
from ...domain.user.repository import UserRepository
from ...core.security import get_password_hash, verify_password, create_access_token
from ...core.dependencies import get_current_user, get_db
from ...core.config import Config

router = APIRouter(prefix="/auth", tags=["認證"])


def get_user_service(db=Depends(get_db)) -> UserService:
    """依賴注入：取得 UserService"""
    repo = UserRepository(db)
    return UserService(repo)


@router.post("/register", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    user_service: UserService = Depends(get_user_service)
):
    """
    用戶註冊
    
    - **username**: 用戶名稱（3-50 字元）
    - **email**: 電子郵件
    - **password**: 密碼（至少 6 字元）
    """
    user = user_service.register_user(user_data, get_password_hash)
    
    return {
        "message": "註冊成功",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """
    用戶登入
    
    返回 JWT access token
    """
    user = user_service.authenticate_user(
        user_data.email,
        user_data.password,
        verify_password
    )
    
    # 生成 JWT Token
    access_token = create_access_token(
        data={"user_id": user["id"]},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token)


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    用戶登入（OAuth2 表單格式）
    
    用於 Swagger UI 的 Authorize 按鈕
    """
    user = user_service.authenticate_user(
        form_data.username,  # OAuth2 使用 username 欄位傳 email
        form_data.password,
        verify_password
    )
    
    access_token = create_access_token(
        data={"user_id": user["id"]},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    取得當前登入用戶資訊
    """
    return UserResponse(**current_user)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    用戶登出
    
    前端應刪除 Token，後端無狀態不需處理
    """
    return {"message": "登出成功"}


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    驗證 Token 是否有效
    """
    return {
        "valid": True,
        "user_id": current_user["id"]
    }
