已為您生成 `src/domain/conversation/` 資料夾的完整函數說明文檔。以下是詳細內容：

## src/domain/conversation/ 模組函數說明

### 📄 schemas.py (Pydantic 模型定義)

| 名稱 | 類型 | 功能說明 |
|------|------|----------|
| ConversationCreate | 類別 | 對話建立請求的數據模型，包含標題欄位驗證 |
| ConversationUpdate | 類別 | 對話更新請求的數據模型，支援更新標題、置頂、封存狀態 |
| ConversationResponse | 類別 | 對話基本資訊回應模型，用於列表顯示 |
| ConversationDetail | 類別 | 對話詳細資訊回應模型（已移除標籤和分享欄位） |
| ChatMessageResponse | 類別 | 聊天訊息回應模型，包含角色、內容和時間戳 |
| ConversationSearchResult | 類別 | 對話搜尋結果模型 |
| ConversationFilter | 類別 | 對話過濾條件模型，支援封存、置頂、日期範圍過濾 |

### 📄 repository.py (資料存取層)

| 名稱 | 功能說明 |
|------|----------|
| `__init__()` | 初始化 Repository，注入資料庫管理器 |
| `create_conversation()` | 在資料庫中建立新對話記錄，返回完整對話資訊 |
| `get_conversation_by_id()` | 根據對話 ID 和用戶 ID 查詢對話，驗證所有權 |
| `get_user_conversations()` | 查詢用戶的所有對話列表，支援封存過濾，按置頂和更新時間排序 |
| `update_conversation()` | 更新對話的標題、置頂、封存狀態，自動更新 updated_at |
| `delete_conversation()` | 刪除對話記錄，CASCADE 會自動刪除關聯的聊天記錄 |
| `update_message_count()` | 更新對話的訊息計數和最後訊息時間 |
| `get_conversation_messages()` | 查詢對話的聊天記錄，支援分頁 |
| `search_conversations()` | 根據關鍵字搜尋對話標題和內容，返回匹配的對話列表 |
| `get_conversation_statistics()` | 取得用戶的對話統計資訊（總數、活躍數、置頂數、總訊息數） |

### 📄 service.py (業務邏輯層)

| 名稱 | 功能說明 |
|------|----------|
| `__init__()` | 初始化 Service，注入 Repository 依賴 |
| `create_conversation()` | 建立新對話的業務邏輯，處理預設標題，返回格式化結果 |
| `get_conversation_detail()` | 取得對話詳細資訊，驗證權限，格式化時間欄位 |
| `list_user_conversations()` | 查詢用戶對話列表，應用多重過濾條件（封存、置頂、日期範圍） |
| `update_conversation_title()` | 更新對話標題，驗證所有權，返回更新結果 |
| `toggle_pin()` | 切換對話置頂狀態，驗證權限，返回新狀態 |
| `toggle_archive()` | 切換對話封存狀態，驗證權限，返回新狀態 |
| `delete_conversation()` | 刪除對話，驗證所有權，協調 Repository 執行刪除 |
| `search_conversations()` | 搜尋對話業務邏輯，驗證搜尋關鍵字，格式化搜尋結果 |
| `get_conversation_messages()` | 取得對話聊天記錄，驗證權限，解析 JSONB 訊息格式 |
| `get_user_statistics()` | 取得用戶對話統計資訊，代理 Repository 方法 |

### 模組架構說明

此模組採用**三層架構**設計：

1. **Schemas 層**：定義 7 個 Pydantic 模型，負責 API 請求/回應的數據驗證
2. **Repository 層**：10 個資料庫操作方法，處理純粹的 SQL 查詢與資料存取
3. **Service 層**：11 個業務邏輯方法，協調 Repository、驗證權限、格式化輸出

總計 **28 個類別/函數**，已移除所有標籤和分享相關功能，適合農會內部部署使用。