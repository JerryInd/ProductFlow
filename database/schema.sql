CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS whatsapp_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    session_data TEXT,
    status TEXT NOT NULL DEFAULT 'disconnected',
    qr_code TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS telegram_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_token TEXT NOT NULL,
    bot_username TEXT,
    bot_name TEXT,
    status TEXT NOT NULL DEFAULT 'disconnected',
    webhook_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL UNIQUE,
    group_name TEXT NOT NULL,
    member_count INTEGER DEFAULT 0,
    last_activity TEXT,
    role TEXT DEFAULT 'member',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    prompt_template TEXT,
    pricing_mode TEXT DEFAULT 'percentage',
    pricing_value REAL DEFAULT 0,
    pricing_tiers TEXT,
    collector_window_seconds INTEGER DEFAULT 90,
    auto_publish INTEGER NOT NULL DEFAULT 1,
    draft_mode INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    group_id TEXT NOT NULL,
    UNIQUE(pipeline_id, group_id)
);

CREATE TABLE IF NOT EXISTS pipeline_destinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    group_id TEXT NOT NULL,
    UNIQUE(pipeline_id, group_id)
);

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER,
    source_group_id TEXT,
    caption TEXT,
    rewritten_caption TEXT,
    media_paths TEXT,
    video_paths TEXT,
    message_ids TEXT,
    price_original INTEGER,
    price_new INTEGER,
    hash TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'collected',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    destination_group_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS processed_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    pipeline_id INTEGER,
    processed_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(message_id, group_id)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    details TEXT,
    level TEXT DEFAULT 'info',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS active_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL,
    source_group_id TEXT NOT NULL,
    media_paths TEXT NOT NULL DEFAULT '[]',
    video_paths TEXT NOT NULL DEFAULT '[]',
    message_ids TEXT NOT NULL DEFAULT '[]',
    caption TEXT NOT NULL DEFAULT '',
    started_at REAL NOT NULL,
    last_msg_at REAL NOT NULL,
    window_seconds INTEGER NOT NULL DEFAULT 90,
    UNIQUE(pipeline_id, source_group_id)
);

CREATE INDEX IF NOT EXISTS idx_products_hash ON products(hash);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status);
CREATE INDEX IF NOT EXISTS idx_processed_messages ON processed_messages(message_id, group_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);

CREATE TABLE IF NOT EXISTS relay_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL,
    destination_group_id TEXT NOT NULL,
    relay_type TEXT NOT NULL,
    media_path TEXT,
    media_caption TEXT DEFAULT '',
    relay_text TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_relay_queue_status ON relay_queue(status);
