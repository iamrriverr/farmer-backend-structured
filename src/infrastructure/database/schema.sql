CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'user', 'guest')),
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);         --加速基於 Email 的查詢（例如登入和找回密碼
CREATE INDEX idx_users_username ON users(username);   --加速基於用戶名的查詢（例如登入）
CREATE INDEX idx_users_is_active ON users(is_active); --加速過濾查詢（例如快速找出所有活躍用戶或非活躍用戶）


-- 更新時間觸發器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    model_config JSONB DEFAULT '{"model": "gpt-4o-mini", "temperature": 0.5}'::jsonb,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id, updated_at DESC); --標準對話列表查詢。加速查詢某用戶的所有對話，並按 最新活動時間降序 排列（即最新聊天的對話顯示在最前面）
CREATE INDEX idx_conversations_user_archived ON conversations(user_id, is_archived, updated_at DESC); --過濾查詢。加速查詢某用戶的所有未封存 (is_archived = FALSE) 或已封存 (is_archived = TRUE) 的對話列表。
CREATE INDEX idx_conversations_user_pinned ON conversations(user_id, is_pinned, updated_at DESC); --置頂查詢。加速查詢某用戶的所有置頂對話，並按活動時間排序。

-- 更新時間觸發器
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations  --	在 conversations 表格上的 UPDATE 操作發生之前執行。
    FOR EACH ROW   --自動更新該行的 updated_at 欄位為當前時間。
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL, --對話 ID。邏輯上對應 conversations.id。雖然您使用了 TEXT 而非 UUID 類型，這通常是為了配合 LangChain 的 PostgresChatMessageHistory 介面，它預設使用 TEXT 來表示 Session ID
    message JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_chat_history_session ON chat_history(session_id, created_at);  --核心查詢索引。用於快速檢索特定對話 (session_id) 的所有訊息，並按時間順序 (created_at) 排序，這是載入聊天畫面所必需的。
CREATE INDEX idx_chat_history_message_gin ON chat_history USING GIN (message); --內容搜索加速。GIN (Generalized Inverted Index) 索引專門用於加速對 JSONB 欄位內部鍵值的查詢。例如，您可以使用這個索引快速搜索特定訊息內容或帶有特定 RAG 來源 ID 的所有訊息。

-- 自動更新對話的 message_count 和 last_message_at
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET message_count = message_count + 1,
        last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE id::text = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversation_stats_trigger
    AFTER INSERT ON chat_history
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_stats();

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'string' CHECK (value_type IN ('string', 'integer', 'boolean', 'json')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, preference_key)
);

-- 索引
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- 更新時間觸發器
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50),
    content_hash VARCHAR(64),
    chunk_count INTEGER DEFAULT 0,
    embedding_model VARCHAR(100) DEFAULT 'models/embedding-001',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_documents_user_id ON documents(user_id, created_at DESC);
CREATE INDEX idx_documents_status ON documents(status, created_at);
CREATE UNIQUE INDEX idx_documents_content_hash ON documents(content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX idx_documents_metadata_gin ON documents USING GIN (metadata);

-- 更新時間觸發器
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#3B82F6',
    icon VARCHAR(50),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- 系統標籤的唯一約束（user_id 為 NULL）
CREATE UNIQUE INDEX idx_tags_system_name ON tags(name) WHERE user_id IS NULL;

-- 索引
CREATE INDEX idx_tags_user_id ON tags(user_id, name);
CREATE INDEX idx_tags_usage_count ON tags(usage_count DESC);

CREATE TABLE conversation_tags (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (conversation_id, tag_id)
);

-- 索引
CREATE INDEX idx_conversation_tags_tag_id ON conversation_tags(tag_id);
CREATE INDEX idx_conversation_tags_conversation_id ON conversation_tags(conversation_id);

-- 自動更新標籤使用次數
CREATE OR REPLACE FUNCTION update_tag_usage_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE id = OLD.tag_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tag_usage_count_trigger
    AFTER INSERT OR DELETE ON conversation_tags
    FOR EACH ROW
    EXECUTE FUNCTION update_tag_usage_count();

CREATE TABLE conversation_shares (
    id SERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    shared_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shared_with INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_level VARCHAR(20) NOT NULL CHECK (permission_level IN ('view', 'comment', 'edit')),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(conversation_id, shared_with),
    CHECK (shared_by != shared_with)
);

-- 索引
CREATE INDEX idx_conversation_shares_shared_with ON conversation_shares(shared_with, is_active);
CREATE INDEX idx_conversation_shares_conversation ON conversation_shares(conversation_id);

-- 更新時間觸發器
CREATE TRIGGER update_conversation_shares_updated_at
    BEFORE UPDATE ON conversation_shares
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE file_processing_queue (
    id BIGSERIAL PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processing_stage VARCHAR(50),
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    total_chunks INTEGER,
    processed_chunks INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(file_id)
);

-- 索引
CREATE INDEX idx_file_processing_user_status ON file_processing_queue(user_id, status, created_at DESC);
CREATE INDEX idx_file_processing_status_retry ON file_processing_queue(status, retry_count);

-- 更新時間觸發器
CREATE TRIGGER update_file_processing_queue_updated_at
    BEFORE UPDATE ON file_processing_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    action_status VARCHAR(20) DEFAULT 'success' CHECK (action_status IN ('success', 'failure', 'pending')),
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(255),
    request_data JSONB,
    response_status INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id, created_at DESC);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- 分區表（按月份分區）
CREATE TABLE audit_logs_y2025m10 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE api_usage_stats (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    token_total INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    window_start TIMESTAMP NOT NULL,
    window_duration INTERVAL NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, endpoint, window_start, window_duration)
);

-- 索引
CREATE INDEX idx_api_usage_user_endpoint ON api_usage_stats(user_id, endpoint, window_start DESC);
CREATE INDEX idx_api_usage_user_window ON api_usage_stats(user_id, window_start);
CREATE INDEX idx_api_usage_created_at ON api_usage_stats(created_at DESC);

CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL CHECK (value_type IN ('string', 'integer', 'boolean', 'json')),
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    is_editable BOOLEAN DEFAULT TRUE,
    validation_rule TEXT,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_system_settings_category ON system_settings(category, is_public);

-- 更新時間觸發器
CREATE TRIGGER update_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    related_entity_type VARCHAR(50),
    related_entity_id VARCHAR(100),
    action_url VARCHAR(500),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    delivery_method JSONB DEFAULT '["in_app"]'::jsonb,
    sent_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_user_type ON notifications(user_id, notification_type, created_at DESC);
CREATE INDEX idx_notifications_expires_at ON notifications(expires_at) WHERE expires_at IS NOT NULL;

-- 自動設定已讀時間
CREATE OR REPLACE FUNCTION set_notification_read_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_read = TRUE AND OLD.is_read = FALSE THEN
        NEW.read_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_notification_read_at_trigger
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION set_notification_read_at();

CREATE TABLE conversation_snapshots (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    snapshot_data JSONB NOT NULL,
    snapshot_version INTEGER DEFAULT 1,
    message_count INTEGER,
    total_tokens INTEGER,
    snapshot_type VARCHAR(20) NOT NULL CHECK (snapshot_type IN ('auto', 'manual', 'pre_delete')),
    created_by INTEGER REFERENCES users(id),
    retention_days INTEGER DEFAULT 90,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_conversation_snapshots_conversation ON conversation_snapshots(conversation_id, created_at DESC);
CREATE INDEX idx_conversation_snapshots_expires_at ON conversation_snapshots(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_conversation_snapshots_data_gin ON conversation_snapshots USING GIN (snapshot_data);

-- 自動設定過期時間
CREATE OR REPLACE FUNCTION set_snapshot_expires_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.expires_at IS NULL THEN
        NEW.expires_at = NEW.created_at + (NEW.retention_days || ' days')::INTERVAL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_snapshot_expires_at_trigger
    BEFORE INSERT ON conversation_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION set_snapshot_expires_at();
