-- Migration: Create jobs table
-- Version: 0001

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    company TEXT NOT NULL,
    website TEXT NOT NULL,
    selected_products TEXT,  -- JSON array of {id, name}
    mode TEXT NOT NULL,      -- 'dry-run' or 'apply'
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    result TEXT,             -- JSON job result
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_jobs_user_email ON jobs(user_email);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Index for recent jobs
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
