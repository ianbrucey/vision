-- ============================================================================
-- Vision — Nested Folder System (v15)
-- ============================================================================
-- Replaces hardcoded flat folders with a hierarchical folder tree.
-- Folders are case-scoped and optionally workspace-scoped.
-- Root folders have parent_id = NULL.

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS folders (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    workspace_id    INTEGER REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    parent_id       INTEGER REFERENCES folders(id) ON DELETE CASCADE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (case_id, workspace_id, parent_id, name)
);

CREATE INDEX IF NOT EXISTS idx_folders_case ON folders (case_id);
CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders (parent_id);
CREATE INDEX IF NOT EXISTS idx_folders_workspace ON folders (workspace_id);

-- Add folder_id to drafts (keep folder TEXT column for backward compat)
ALTER TABLE drafts ADD COLUMN IF NOT EXISTS folder_id
    INTEGER REFERENCES folders(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_drafts_folder ON drafts (folder_id);

INSERT INTO schema_migrations (version, name) VALUES (16, 'add_nested_folders')
ON CONFLICT (version) DO NOTHING;
