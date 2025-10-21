完美！我已經檢查了您的 `src/core/` 模組並生成了完整的函數說明文檔。以下是檢查結果與文檔摘要：

## ✅ 檔案檢查結果

您的 `src/core/` 模組結構完整且正確，包含 5 個檔案：

1. ✅ **config.py** - 系統配置管理（完整）
2. ✅ **security.py** - 安全模組（完整）
3. ✅ **dependencies.py** - 依賴注入（完整）
4. ✅ **exceptions.py** - 自定義異常（完整）
5. ✅ **__init__.py** - 模組入口（完整）

## 📊 模組功能統計

| 模組 | 類別 | 函數/方法 | 功能 |
|------|-----|---------|------|
| config.py | 1 (Config) | 3 | 配置管理 |
| security.py | 0 | 5 | 密碼加密與 JWT |
| dependencies.py | 0 | 5 | FastAPI 依賴注入 |
| exceptions.py | 7 | 0 | 業務異常定義 |
| **總計** | **8** | **13** | **核心功能** |

## 📄 完整說明文檔

### 1. Config 類別（config.py）

**配置分類（共 13 組配置）**：
- 系統基本設定、JWT 認證、OpenAI API、Google AI
- PostgreSQL、Chroma 向量資料庫、檔案上傳
- RAG 設定、農會內網部署、日誌、資料保留、CORS

**方法**：
- `validate()` - 驗證必要配置
- `get_model_name()` - 取得 LLM 模型名稱
- `print_config()` - 列印配置（隱藏敏感資訊）

### 2. 安全函數（security.py）

| 函數 | 功能 | 使用場景 |
|------|------|---------|
| `verify_password()` | 驗證密碼 | 用戶登入 |
| `get_password_hash()` | 加密密碼 | 用戶註冊 |
| `create_access_token()` | 生成 JWT | 登入成功 |
| `decode_access_token()` | 解碼 JWT | API 驗證 |
| `verify_websocket_token()` | WebSocket 驗證 | WS 連線 |

### 3. 依賴注入（dependencies.py）

| 依賴函數 | 返回值 | 使用場景 |
|---------|--------|---------|
| `get_current_user()` | 完整用戶資訊 | 所有需要身份驗證的端點 |
| `get_current_active_user()` | 啟用用戶資訊 | 需確保帳號啟用的端點 |
| `get_current_admin_user()` | 管理員資訊 | 管理員專用端點 |
| `get_db()` | 資料庫連線 | 所有資料庫操作 |
| `verify_websocket_token()` | 用戶資訊 | WebSocket 端點 |

### 4. 異常類別（exceptions.py）

| 異常 | HTTP 狀態碼 | 使用場景 |
|------|------------|---------|
| `BusinessException` | 自定義 | 基類 |
| `ResourceNotFoundException` | 404 | 資源不存在 |
| `UnauthorizedException` | 401 | 未授權 |
| `ForbiddenException` | 403 | 權限不足 |
| `ValidationException` | 400 | 驗證失敗 |
| `DuplicateResourceException` | 409 | 資源重複 |
| `ServiceUnavailableException` | 503 | 服務不可用 |

## 📁 已生成的文檔檔案

1.  `core_config_methods_documentation.csv` - Config 方法說明
2.  `core_security_functions_documentation.csv` - 安全函數說明
3.  `core_dependencies_documentation.csv` - 依賴注入說明
4.  `core_exceptions_documentation.csv` - 異常類別說明


1. ✅ 配置管理完整（13 組配置涵蓋所有需求）
2. ✅ 安全機制健全（Argon2 + JWT）
3. ✅ 依賴注入規範（符合 FastAPI 最佳實踐）
4. ✅ 異常處理完善（7 種業務異常覆苻所有場景）
5. ✅ 模組匯出清晰（__init__.py 統一管理）