已為您生成 `src/domain/chat/` 模組的完整函數說明文檔。以下是完整的文檔內容：

# src/domain/chat/ 模組完整函數說明文檔

## 檔案總覽

該模組包含 6 個檔案，共計 **7 個類別** 和 **32 個函數/方法**，負責整個聊天系統的業務邏輯。

***

## 1. schemas.py - 數據模型定義

### Pydantic 模型類別（7個）

**ChatRequest** - 聊天請求模型
- question: str（1-2000字元）
- conversation_id: Optional[str]（用於記憶）
- k: int（RAG檢索數量，預設5，範圍1-20）

**ChatSource** - 來源文件模型
- source: str（文件名稱）
- department: Optional[str]（部門）
- content: str（內容片段）

**ChatResponse** - 聊天回應模型
- answer: str（AI回答）
- sources: List[ChatSource]
- context_count: int
- conversation_id, intent

**ChatMessageResponse** - 單條訊息模型
- role, content, timestamp, sources

**IntentResult** - 意圖分類結果
- use_rag: bool
- type: str（rag/chitchat/out_of_scope）
- confidence: float（0.0-1.0）
- reason: str

**WebSocketMessage** - WebSocket訊息格式

**StreamChunk** - 串流片段

***

## 2. repository.py - 資料存取層

### ChatRepository 類別

**核心方法**：

1. **`save_message(conversation_id, role, content, sources, intent)`**
   - 儲存聊天訊息到 chat_history 表
   - 支援儲存來源文件和意圖分類結果（JSONB格式）

2. **`get_chat_history(conversation_id, limit=100, offset=0)`**
   - 取得對話記錄（按時間升序）
   - 返回：List[Dict] 包含完整訊息資訊

3. **`get_recent_history(conversation_id, limit=10)`**
   - 取得最近 N 條記錄用於上下文
   - 返回：List[Tuple[str, str]] 格式 (role, content)

4. **`clear_chat_history(conversation_id)`**
   - 清空指定對話的所有記錄

5. **`get_message_count(conversation_id)`**
   - 統計訊息總數

6. **`update_conversation_stats(conversation_id, user_id, message_increment=2)`**
   - 更新 conversations 表的統計資訊
   - 包含訊息數、最後訊息時間

***

## 3. service.py - 業務邏輯層

### ChatService 類別

**核心方法**：

1. **`process_query(request, user_id) -> ChatResponse`**
   - REST API 非串流查詢
   - 流程：意圖分類 → 載入歷史 → RAG/閒聊 → 儲存記錄
   - 返回完整的 ChatResponse

2. **`process_streaming_query(request, user_id) -> AsyncGenerator`**
   - WebSocket/SSE 串流查詢
   - Yield 順序：intent → sources → chunks → done

3. **`get_conversation_history(conversation_id, user_id, limit, offset)`**
   - 取得並格式化對話歷史為 API 格式

4. **`clear_conversation_history(conversation_id, user_id)`**
   - 清空對話（含權限驗證）

**內部輔助方法**：

- `_format_history(history)` - 格式化歷史為 LLM 可讀文字
- `_handle_out_of_scope()` - 超範圍回應模板
- `_process_with_rag(question, history, k)` - RAG 處理
- `_process_chitchat(question, history)` - 閒聊處理

***

## 4. rag_engine.py - RAG 核心引擎

### RAGEngine 類別

**初始化**：
- 根據 config 選擇 LLM（GPT/Gemini）
- 定義 RAG Prompt 和 Chitchat Prompt
- 初始化串流與非串流 LLM 實例

**核心方法**：

1. **`query(question, history, k, metadata_filter) -> Dict`**
   - 非串流 RAG 查詢
   - 流程：向量檢索 → 格式化上下文 → LLM生成 → 返回結果
   - 返回：{answer, sources, context_count}

2. **`generate_stream(question, history, k, metadata_filter) -> AsyncGenerator`**
   - 串流 RAG 查詢
   - Yield: sources → chunk × N

3. **`chitchat(question, history) -> str`**
   - 非串流閒聊回應
   - 使用專門的閒聊 Prompt

4. **`generate_chitchat_stream(question, history) -> AsyncGenerator`**
   - 串流閒聊回應

**內部方法**：

- `_format_context(docs)` - 格式化檢索結果
  - 格式：【資料1】來源：xxx 部門：xxx 內容：xxx

***

## 5. intent_classifier.py - 意圖分類器

### IntentClassifier 類別

**初始化**：
- 使用 Gemini Flash 8B 模型（快速、低成本）
- 定義詳細的分類 Prompt（包含農業領域範例）

**核心方法**：

1. **`classify(query) -> Dict`**
   - 分類用戶問題為三種類型
   - RAG：需要查詢文件（農業技術、政策補助等）
   - CHITCHAT：一般對話（問候、閒聊）
   - OUT_OF_SCOPE：超出服務範圍
   - 返回：{use_rag, type, confidence, reason}

2. **`extract_metadata_filter(query) -> Dict`**
   - 從問題中提取過濾條件
   - 檢測部門：信用/保險/供銷/推廣
   - 檢測年份：正則表達式匹配

**內部方法**：

- `_parse_response(response)` - 解析 LLM JSON 回應（含容錯）

***

## 6. hybrid_search.py - 混合搜尋引擎

### ChineseTextPreprocessor 類別

**初始化**：
- 載入 50+ 農業專業詞彙
- 定義停用詞表（20+ 常用詞）

**方法**：

1. **`tokenize(text) -> List[str]`**
   - 中文分詞（jieba）
   - 過濾：停用詞、單字符、符號

### HybridSearchEngine 類別

**初始化**：
- 設定 BM25 與向量搜尋的權重（預設各0.5）

**核心方法**：

1. **`search(query, documents, vector_scores, top_k) -> List[Document]`**
   - 混合搜尋主方法
   - 流程：BM25分數 → 加權結合 → 排序 → Top-K
   - 返回排序後的文件列表

**內部方法**：

- `_bm25_search(query, documents)` - BM25 關鍵字搜尋
  - 計算詞頻 → 簡化 BM25 公式 → 正規化

***

## 使用流程示例

### REST API 查詢流程
```
用戶請求 → ChatService.process_query()
  ↓
IntentClassifier.classify() - 判斷意圖
  ↓
ChatRepository.get_recent_history() - 載入歷史
  ↓
RAGEngine.query() / chitchat() - 生成回答
  ↓
ChatRepository.save_message() - 儲存記錄
  ↓
返回 ChatResponse
```

### WebSocket 串流流程
```
用戶連接 → ChatService.process_streaming_query()
  ↓
Yield: intent 結果
  ↓
RAGEngine.generate_stream()
  ↓
Yield: sources → chunk1 → chunk2 → ... → done
  ↓
ChatRepository.save_message() - 儲存完整回答
```

這份文檔涵蓋了 chat 模組的所有核心功能和 API 接口，方便後續維護和擴展。