# tests/test_core/test_security.py
"""
測試安全模組功能
"""

import pytest
from src.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token
)
from datetime import timedelta


class TestPasswordHashing:
    """密碼加密測試"""
    
    def test_hash_password(self):
        """測試密碼加密"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_success(self):
        """測試密碼驗證（成功）"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """測試密碼驗證（失敗）"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWT:
    """JWT Token 測試"""
    
    def test_create_token(self):
        """測試建立 Token"""
        data = {"user_id": 1, "username": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token(self):
        """測試解碼 Token"""
        data = {"user_id": 1, "username": "testuser"}
        token = create_access_token(data)
        
        decoded = decode_access_token(token)
        
        assert decoded["user_id"] == 1
        assert decoded["username"] == "testuser"
    
    def test_decode_invalid_token(self):
        """測試解碼無效 Token"""
        invalid_token = "invalid.token.string"
        
        decoded = decode_access_token(invalid_token)
        
        assert decoded is None
    
    def test_token_expiration(self):
        """測試 Token 過期"""
        data = {"user_id": 1}
        # 建立已過期的 token（-1 秒）
        token = create_access_token(data, timedelta(seconds=-1))
        
        decoded = decode_access_token(token)
        
        # 過期的 token 應該返回 None
        assert decoded is None
