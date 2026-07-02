ALTER TABLE pdf_index ADD COLUMN provider_type TEXT;          -- "local", "google_drive", etc.
ALTER TABLE pdf_index ADD COLUMN root_id TEXT;                -- identifier for the root (e.g., "local_home")
ALTER TABLE pdf_index ADD COLUMN account_id TEXT;             -- e.g., "personal@email.com"
ALTER TABLE pdf_index ADD COLUMN remote_id TEXT;              -- provider‑specific file ID (e.g., Google Drive fileId)
ALTER TABLE pdf_index ADD COLUMN remote_path TEXT;            -- logical path within provider
ALTER TABLE pdf_index ADD COLUMN remote_modified_time REAL;   -- provider's modified timestamp
ALTER TABLE pdf_index ADD COLUMN sync_status TEXT;            -- "synced", "pending_download", "deleted", etc.
ALTER TABLE pdf_index ADD COLUMN cached_local_path TEXT;      -- path to locally cached copy

-- New table for sync state per root
CREATE TABLE sync_state (
    root_id TEXT PRIMARY KEY,
    provider_type TEXT,
    account_id TEXT,
    last_sync_time REAL,
    sync_token TEXT,            -- for incremental sync (e.g., Google Drive changes page token)
    last_full_scan_time REAL
);