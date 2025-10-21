# src/api/v1/users.py
"""
用戶管理 API 路由
處理用戶資料、偏好設定、通知等（移除標籤相關端點）
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict

from ...domain.user.schemas import UserUpdate, UserProfile, PasswordChange, PreferencesUpdate
from ...domain.user.service import UserService
from ...domain.user.repository import UserRepository
from ...core.dependencies import get_current_user, get_db
from ...core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["用戶管理"])


def get_user_service(db=Depends(get_db)) -> UserService:
    """依賴注入：取得 UserService"""
    repo = UserRepository(db)
    return UserService(repo)


@router.get("/me/profile", response_model=Dict)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    取得當前用戶的完整資料
    
    包含基本資訊、統計數據、偏好設定等
    """
    return user_service.get_user_profile(current_user["id"])


@router.patch("/me/profile")
async def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    更新當前用戶資料
    """
    updated_user = user_service.update_user_profile(
        current_user["id"],
        update_data
    )
    
    return {
        "message": "資料已更新",
        "user": updated_user
    }


@router.post("/me/password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    修改密碼
    """
    user_service.change_password(
        current_user["id"],
        password_data,
        verify_password,
        get_password_hash
    )
    
    return {"message": "密碼已更新"}


@router.get("/me/preferences")
async def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    取得用戶偏好設定
    """
    preferences = user_service.get_user_preferences(current_user["id"])
    return {"preferences": preferences}


@router.put("/me/preferences")
async def update_user_preferences(
    preferences_data: PreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用戶偏好設定
    """
    user_service.update_user_preferences(
        current_user["id"],
        preferences_data.preferences
    )
    
    return {"message": "偏好設定已更新"}


@router.get("/me/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    取得用戶統計資訊
    """
    stats = user_service.get_user_statistics(current_user["id"])
    return stats


# ============================================================
# 管理員功能
# ============================================================

@router.get("/", response_model=List[Dict])
async def get_all_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    取得所有用戶列表（管理員功能）
    """
    # 檢查權限
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    
    users = user_service.get_all_users(limit, offset)
    return users


@router.patch("/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    切換用戶啟用狀態（管理員功能）
    """
    # 檢查權限
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    
    result = user_service.toggle_user_active(user_id)
    
    return {
        "message": f"用戶 {result['username']} 已{'停用' if not result['is_active'] else '啟用'}",
        "user": result
    }
