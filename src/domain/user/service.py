# src/domain/user/service.py
"""
用戶業務邏輯層 (Service)
處理用戶相關的業務邏輯，協調 Repository 與外部服務
"""

from typing import Dict, Optional, List
from fastapi import HTTPException, status
from .repository import UserRepository
from .schemas import UserRegister, UserLogin, UserUpdate, PasswordChange


class UserService:
    """用戶業務邏輯類別"""
    
    def __init__(self, repository: UserRepository):
        """
        初始化 Service
        
        Args:
            repository: UserRepository 實例
        """
        self.repo = repository
    
    def register_user(self, user_data: UserRegister, password_hasher) -> Dict:
        """
        註冊新用戶
        
        Args:
            user_data: 用戶註冊資料
            password_hasher: 密碼加密函數
            
        Returns:
            Dict: 新建用戶資訊
            
        Raises:
            HTTPException: 當 email 或 username 已存在時
        """
        # 檢查 email 是否已存在
        if self.repo.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此 Email 已被註冊"
            )
        
        # 檢查 username 是否已存在
        if self.repo.get_user_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此用戶名稱已被使用"
            )
        
        # 加密密碼
        hashed_password = password_hasher(user_data.password)
        
        # 建立用戶
        user = self.repo.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role="user"
        )
        
        # 建立預設偏好設定
        self.repo.create_default_preferences(user["id"])
        
        return user
    
    def authenticate_user(self, email: str, password: str, password_verifier) -> Dict:
        """
        驗證用戶登入
        
        Args:
            email: 電子郵件
            password: 密碼
            password_verifier: 密碼驗證函數
            
        Returns:
            Dict: 用戶資訊
            
        Raises:
            HTTPException: 當驗證失敗時
        """
        # 查詢用戶
        user = self.repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email 或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 驗證密碼
        if not password_verifier(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email 或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 檢查帳號是否啟用
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="帳號已被停用，請聯繫管理員"
            )
        
        # 更新最後登入時間
        self.repo.update_last_login(user["id"])
        
        return user
    
    def get_user_profile(self, user_id: int) -> Dict:
        """
        取得用戶完整資料
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 包含用戶資訊、統計數據、偏好設定
        """
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用戶不存在"
            )
        
        # 取得統計資訊
        statistics = self.repo.get_user_statistics(user_id)
        
        # 取得偏好設定
        preferences = self.repo.get_user_preferences(user_id)
        
        return {
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "is_active": user["is_active"],
                "created_at": user["created_at"].isoformat(),
                "last_login_at": user["last_login_at"].isoformat() if user.get("last_login_at") else None
            },
            "statistics": statistics,
            "preferences": preferences
        }
    
    def update_user_profile(self, user_id: int, update_data: UserUpdate) -> Dict:
        """
        更新用戶資料
        
        Args:
            user_id: 用戶 ID
            update_data: 更新資料
            
        Returns:
            Dict: 更新後的用戶資訊
            
        Raises:
            HTTPException: 當更新失敗時
        """
        update_dict = update_data.dict(exclude_unset=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供一個更新欄位"
            )
        
        # 檢查 username 是否已被其他用戶使用
        if 'username' in update_dict:
            existing_user = self.repo.get_user_by_username(update_dict['username'])
            if existing_user and existing_user['id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="用戶名稱已被使用"
                )
        
        # 檢查 email 是否已被其他用戶使用
        if 'email' in update_dict:
            existing_user = self.repo.get_user_by_email(update_dict['email'])
            if existing_user and existing_user['id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email 已被使用"
                )
        
        return self.repo.update_user(user_id, **update_dict)
    
    def change_password(self, user_id: int, password_data: PasswordChange, 
                       password_verifier, password_hasher):
        """
        修改密碼
        
        Args:
            user_id: 用戶 ID
            password_data: 密碼修改資料
            password_verifier: 密碼驗證函數
            password_hasher: 密碼加密函數
            
        Raises:
            HTTPException: 當舊密碼錯誤時
        """
        user = self.repo.get_user_by_id(user_id)
        
        # 驗證舊密碼
        if not password_verifier(password_data.old_password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="舊密碼錯誤"
            )
        
        # 加密新密碼並更新
        new_hashed_password = password_hasher(password_data.new_password)
        self.repo.update_user(user_id, hashed_password=new_hashed_password)
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """
        取得用戶統計資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 統計資訊
        """
        return self.repo.get_user_statistics(user_id)
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        取得用戶偏好設定
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 偏好設定
        """
        return self.repo.get_user_preferences(user_id)
    
    def update_user_preferences(self, user_id: int, preferences: Dict):
        """
        更新用戶偏好設定
        
        Args:
            user_id: 用戶 ID
            preferences: 偏好設定字典
        """
        self.repo.update_user_preferences(user_id, preferences)
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        取得所有用戶列表（管理員功能）
        
        Args:
            limit: 返回數量限制
            offset: 分頁偏移量
            
        Returns:
            List[Dict]: 用戶列表
        """
        return self.repo.get_all_users(limit, offset)
    
    def toggle_user_active(self, user_id: int) -> Dict:
        """
        切換用戶啟用狀態（管理員功能）
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict: 更新後的用戶資訊
        """
        result = self.repo.toggle_user_active(user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用戶不存在"
            )
        return result
