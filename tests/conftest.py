# tests/conftest.py
"""
Pytest 配置和共用 Fixtures
"""

import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from src.core.config import Config
from src.infrastructure import DatabaseConnection, VectorStoreManager


# ============================================================
# 環境變數設定（測試模式）
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """設定測試環境變數"""
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["PG_DATABASE"] = "farmer_test"
    os.environ["INTERNAL_NETWORK_ONLY"] = "false"


# ============================================================
# FastAPI 測試客戶端
# ============================================================

@pytest.fixture(scope="module")
def client():
    """FastAPI 測試客戶端"""
    with TestClient(app) as test_client:
        yield test_client


# ============================================================
# 資料庫 Fixtures
# ============================================================

@pytest.fixture(scope="function")
def mock_db():
    """模擬資料庫連線"""
    mock = Mock(spec=DatabaseConnection)
    mock.get_connection = MagicMock()
    mock.execute_query = MagicMock()
    mock.test_connection = MagicMock(return_value=True)
    return mock


@pytest.fixture(scope="function")
def real_db():
    """真實資料庫連線（需要本地資料庫）"""
    try:
        db = DatabaseConnection(Config)
        yield db
        db.close_pool()
    except Exception as e:
        pytest.skip(f"資料庫連線失敗，跳過測試: {e}")


# ============================================================
# 向量資料庫 Fixtures
# ============================================================

@pytest.fixture(scope="function")
def mock_vector_store():
    """模擬向量資料庫"""
    mock = Mock(spec=VectorStoreManager)
    mock.add_documents = MagicMock(return_value=["doc1", "doc2"])
    mock.similarity_search = MagicMock(return_value=[])
    mock.get_collection_count = MagicMock(return_value=0)
    return mock


# ============================================================
# 測試用戶 Fixtures
# ============================================================

@pytest.fixture
def test_user():
    """測試用戶資料"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "full_name": "Test User",
        "department": "測試部門"
    }


@pytest.fixture
def test_admin():
    """測試管理員資料"""
    return {
        "username": "admin",
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "role": "admin"
    }


# ============================================================
# JWT Token Fixtures
# ============================================================

@pytest.fixture
def auth_headers(client, test_user):
    """
    取得認證 headers
    （實際測試時需要先註冊並登入）
    """
    # 註冊用戶
    client.post("/api/v1/auth/register", json=test_user)
    
    # 登入取得 token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        pytest.skip("無法取得認證 token")


# ============================================================
# 測試資料 Fixtures
# ============================================================

@pytest.fixture
def sample_document():
    """範例文件資料"""
    return {
        "filename": "test_document.pdf",
        "content": "這是一份測試文件內容...",
        "department": "業務部",
        "metadata": {
            "author": "測試作者",
            "date": "2025-10-18"
        }
    }


@pytest.fixture
def sample_chat_request():
    """範例聊天請求"""
    return {
        "question": "如何申請農業補助？",
        "conversation_id": None,
        "k": 5
    }
