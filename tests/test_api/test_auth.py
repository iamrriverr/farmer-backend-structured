# tests/test_api/test_auth.py
"""
測試認證 API
"""

import pytest
from fastapi.testclient import TestClient


class TestAuthRegister:
    """測試用戶註冊"""
    
    def test_register_success(self, client, test_user):
        """測試註冊成功"""
        response = client.post("/api/v1/auth/register", json=test_user)
        
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "user_id" in data
    
    def test_register_duplicate_username(self, client, test_user):
        """測試註冊重複用戶名"""
        # 第一次註冊
        client.post("/api/v1/auth/register", json=test_user)
        
        # 第二次註冊（應該失敗）
        response = client.post("/api/v1/auth/register", json=test_user)
        
        assert response.status_code == 400
    
    def test_register_invalid_email(self, client):
        """測試註冊無效郵箱"""
        invalid_data = {
            "username": "testuser",
            "email": "invalid-email",  # 無效郵箱
            "password": "TestPass123!"
        }
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # 驗證錯誤


class TestAuthLogin:
    """測試用戶登入"""
    
    def test_login_success(self, client, test_user):
        """測試登入成功"""
        # 先註冊
        client.post("/api/v1/auth/register", json=test_user)
        
        # 登入
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, test_user):
        """測試登入錯誤密碼"""
        # 先註冊
        client.post("/api/v1/auth/register", json=test_user)
        
        # 使用錯誤密碼登入
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """測試登入不存在的用戶"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401


class TestAuthVerify:
    """測試 Token 驗證"""
    
    def test_verify_valid_token(self, client, auth_headers):
        """測試驗證有效 Token"""
        response = client.get("/api/v1/auth/verify", headers=auth_headers)
        
        assert response.status_code == 200
    
    def test_verify_invalid_token(self, client):
        """測試驗證無效 Token"""
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/v1/auth/verify", headers=invalid_headers)
        
        assert response.status_code == 401
    
    def test_verify_missing_token(self, client):
        """測試缺少 Token"""
        response = client.get("/api/v1/auth/verify")
        
        assert response.status_code == 401
