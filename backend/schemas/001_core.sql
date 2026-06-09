-- ============================================================================
-- Vision — Database Schema v1.0
-- ============================================================================
-- The foundation of the War Room Agent. This schema defines the data contract
-- that every script, tool, and agent reads from or writes to.
--
-- Design principles reflected here:
--   1. Citation-anchored everything — every fact links back to a block
--   2. Domain-agnostic evidence layer — documents/sections/blocks are universal
--   3. Progressive structure — unstructured PDF → semi-structured blocks →
--      structured case entities
--   4. Workspace-aware — nullable workspace_id on everything that can be scoped
--   5. The agent owns its workspace — dedicated schema with write access
--
-- Dependencies:
--   - PostgreSQL 15+
--   - pgvector extension (for vector embeddings)
--   - pg_trgm extension (for fuzzy text search on titles)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Extensions
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ----------------------------------------------------------------------------
-- Schemas
-- ----------------------------------------------------------------------------
-- vision      — case core + evidence store (this schema)
-- agent_work  — agent-scoped working tables (created/destroyed per session)

CREATE SCHEMA IF NOT EXISTS vision;
CREATE SCHEMA IF NOT EXISTS agent_work;

-- Set search path so unqualified references hit the right schema
SET search_path TO vision, agent_work, public;

-- ============================================================================
-- CASE CORE
-- ============================================================================
-- The structured entities that are true for every case regardless of domain.
-- Populated by the user (upfront) and the agent (as it works).
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- cases — The container. One row per matter.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cases (
    id              SERIAL PRIMARY KEY,
    external_id     UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,  -- for URLs/API refs
    name            TEXT NOT NULL,                                   -- human-readable label
    case_number     TEXT,                                            -- optional. may not exist.
    case_type       TEXT NOT NULL CHECK (case_type IN (
                        'medical_board_complaint',
                        'civil_litigation',
                        'pre_litigation_investigation',
                        'internal_investigation',
                        'e_discovery',
                        'rfp_response',
                        'contract_review',
                        'insurance_claim',
                        'regulatory_response',
                        'other'
                    )),
    status          TEXT NOT NULL DEFAULT 'intake' CHECK (status IN (
                        'intake',       -- documents being ingested
                        'indexing',     -- evidence store being populated
                        'analyzing',    -- agent actively reviewing
                        'drafting',     -- output being generated
                        'complete',     -- delivered
                        'archived'      -- done, kept for reference
                    )),
    jurisdiction    TEXT,                                            -- where filed, if applicable
    filing_date     DATE,                                            -- when filed, if applicable
    description     TEXT,                                            -- 1-2 sentence summary
    narrative       TEXT,                                            -- the user's raw brain dump
    case_brief      JSONB,                                           -- extracted structured brief
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cases_case_type ON cases (case_type);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases (status);
CREATE INDEX IF NOT EXISTS idx_cases_external_id ON cases (external_id);

-- ----------------------------------------------------------------------------
-- parties — People and organizations. Roles are tags, not categories.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parties (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,
    party_kind      TEXT NOT NULL CHECK (party_kind IN ('individual', 'organization')),
    roles           TEXT[] NOT NULL DEFAULT '{}',                     -- tags: plaintiff, respondent, witness, expert, etc.
    contact_info    JSONB,                                            -- phone, email, address
    notes           TEXT,                                             -- free-text about their role in the case
    discovered_by   TEXT NOT NULL DEFAULT 'user' CHECK (discovered_by IN ('user', 'agent')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_parties_case_id ON parties (case_id);
CREATE INDEX IF NOT EXISTS idx_parties_roles ON parties USING GIN (roles);
CREATE INDEX IF NOT EXISTS idx_parties_name ON parties (case_id, name);

-- ----------------------------------------------------------------------------
-- allegations — Numbered claims or key questions that drive the review.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS allegations (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    allegation_id   TEXT NOT NULL,                                    -- human-readable: 'A01', 'A02'
    text            TEXT NOT NULL,                                    -- the allegation
    category        TEXT CHECK (category IN (
                        'diagnostic_delay', 'surgical_error', 'informed_consent',
                        'post_op_management', 'documentation', 'communication',
                        'medication_error', 'failure_to_diagnose', 'failure_to_treat',
                        'negligent_referral', 'negligent_credentialing',
                        'breach_of_contract', 'negligence', 'fraud',
                        'breach_of_warranty', 'strict_liability',
                        'discrimination', 'retaliation',
                        'other'
                    )),
    targets         INTEGER[] DEFAULT '{}',                           -- party IDs this allegation is against
    status          TEXT DEFAULT 'pending' CHECK (status IN (
                        'pending',      -- not yet reviewed
                        'supported',    -- evidence supports the allegation
                        'contradicted', -- evidence contradicts it
                        'silent',       -- no evidence either way
                        'partial'       -- some support, some contradiction
                    )),
    verdict         JSONB,                                            -- full reasoning output from the agent
    extraction_focus TEXT[],                                           -- what to look for in the record
    sort_order      INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (case_id, allegation_id)
);

CREATE INDEX IF NOT EXISTS idx_allegations_case_id ON allegations (case_id);
CREATE INDEX IF NOT EXISTS idx_allegations_status ON allegations (case_id, status);

-- ============================================================================
-- EVIDENCE STORE
-- ============================================================================
-- The universal document model. A medical record, a contract, and a credit
-- report all become: documents → sections → blocks. Domain-agnostic.
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- documents — Uploaded files. One row per file ingested into the system.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    workspace_id    INTEGER,                                          -- deferred: FK to workspaces
    name            TEXT NOT NULL,                                    -- original filename
    storage_path    TEXT,                                             -- S3 key or local filesystem path
    page_count      INTEGER,                                          -- total pages
    document_type   TEXT,                                             -- inferred: medical_record, complaint, contract, email, etc.
    source          TEXT DEFAULT 'user_upload' CHECK (source IN (
                        'user_upload', 'discovery', 'data_lab', 'email',
                        'portal', 'api', 'other'
                    )),
    ocr_status      TEXT DEFAULT 'pending' CHECK (ocr_status IN (
                        'pending', 'processing', 'complete', 'failed'
                    )),
    ocr_provider    TEXT DEFAULT 'datalab',                           -- which OCR engine
    ocr_result_path TEXT,                                             -- path to the datalab.json output
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (case_id, name)
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents (case_id);
CREATE INDEX IF NOT EXISTS idx_documents_workspace ON documents (workspace_id);
CREATE INDEX IF NOT EXISTS idx_documents_ocr_status ON documents (ocr_status);

-- ----------------------------------------------------------------------------
-- sections — Structural hierarchy of each document. The table of contents.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sections (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    datalab_id      TEXT,                                             -- e.g. "/page/7/SectionHeader/3"
    parent_id       INTEGER REFERENCES sections(id) ON DELETE CASCADE, -- tree structure
    heading_level   INTEGER CHECK (heading_level BETWEEN 0 AND 6),    -- H1-H6 for markdown-style headers
    title           TEXT,                                             -- stripped HTML from the SectionHeader block
    page_start      INTEGER NOT NULL,                                 -- page where this section begins
    page_end        INTEGER,                                          -- page where it ends (or NULL if last section)
    block_count     INTEGER DEFAULT 0,                                -- how many blocks in this section
    -- Text for embedding: title + concatenated child block text
    search_text     TEXT,
    -- Mistral embed dimension. Null until populated. Null means "not embedded yet."
    embedding       VECTOR(1024),
    -- Heading chain as an array for fast lookups without recursive CTEs.
    -- e.g., ["Visits", "Operative Report", "Findings"]
    heading_chain   TEXT[],
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sections_document ON sections (document_id);
CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections (parent_id);
CREATE INDEX IF NOT EXISTS idx_sections_heading ON sections (heading_level);
CREATE INDEX IF NOT EXISTS idx_sections_page_range ON sections (document_id, page_start, page_end);
-- Embedding index for semantic search
CREATE INDEX IF NOT EXISTS idx_sections_embedding ON sections USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
-- GIN trigram for title autocomplete and fuzzy matching
CREATE INDEX IF NOT EXISTS idx_sections_title_trgm ON sections USING GIN (title gin_trgm_ops);
-- Full-text search on section titles
ALTER TABLE sections ADD COLUMN IF NOT EXISTS title_tsv TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, ''))) STORED;
CREATE INDEX IF NOT EXISTS idx_sections_title_tsv ON sections USING GIN (title_tsv);

-- ----------------------------------------------------------------------------
-- blocks — Every text fragment from DataLab. The atomic unit of citation.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blocks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    datalab_id      TEXT,                                             -- e.g. "/page/116/Text/6" — the canonical external ref
    section_id      INTEGER REFERENCES sections(id) ON DELETE SET NULL,
    block_type      TEXT NOT NULL,  -- validated at application layer
    page            INTEGER NOT NULL,
    -- The original HTML from DataLab. Preserved for rendering.
    html_content    TEXT,
    -- Stripped plain text. What the agent reads and what gets FTS-indexed.
    text_content    TEXT,
    -- Bounding box on the page. For spatial queries and PDF highlighting.
    bbox_x1         FLOAT,
    bbox_y1         FLOAT,
    bbox_x2         FLOAT,
    bbox_y2         FLOAT,
    -- Full-text search vector. Automatically updated.
    text_tsv        TSVECTOR GENERATED ALWAYS AS (
                        to_tsvector('english', coalesce(text_content, ''))
                    ) STORED,
    -- Optional per-block embedding (for block-level semantic search).
    -- Most searches use section-level embeddings. Block-level is for
    -- fine-grained retrieval when sections are large.
    embedding       VECTOR(1024),
    metadata        JSONB DEFAULT '{}'
);

-- Lookup indexes
CREATE INDEX IF NOT EXISTS idx_blocks_document ON blocks (document_id);
CREATE INDEX IF NOT EXISTS idx_blocks_section ON blocks (section_id);
CREATE INDEX IF NOT EXISTS idx_blocks_page ON blocks (document_id, page);
CREATE INDEX IF NOT EXISTS idx_blocks_type ON blocks (block_type);
CREATE INDEX IF NOT EXISTS idx_blocks_datalab_id ON blocks (datalab_id);
-- Full-text search
CREATE INDEX IF NOT EXISTS idx_blocks_tsv ON blocks USING GIN (text_tsv);
-- Block-level embedding index (may stay empty for most blocks)
CREATE INDEX IF NOT EXISTS idx_blocks_embedding ON blocks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ----------------------------------------------------------------------------
-- block_headings — Heading ancestry for every block.
-- ----------------------------------------------------------------------------
-- A block on page 117 might be inside: H1 "Visits" → H2 "Operative Report" →
-- H3 "Findings". This table stores that ancestry so the agent can ask:
-- "What section contains block X?" without a recursive CTE every time.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS block_headings (
    block_id        INTEGER REFERENCES blocks(id) ON DELETE CASCADE NOT NULL,
    section_id      INTEGER REFERENCES sections(id) ON DELETE CASCADE NOT NULL,
    heading_level   INTEGER NOT NULL CHECK (heading_level BETWEEN 0 AND 6),
    -- The depth of this heading in the chain. 1 = closest ancestor, N = root.
    -- A block directly inside an H3 has heading_level 3 in the row with depth 1.
    depth           INTEGER NOT NULL DEFAULT 1,

    PRIMARY KEY (block_id, section_id, heading_level)
);

CREATE INDEX IF NOT EXISTS idx_block_headings_section ON block_headings (section_id);
CREATE INDEX IF NOT EXISTS idx_block_headings_level ON block_headings (block_id, depth);

-- ============================================================================
-- CITATIONS — The link layer.
-- ============================================================================
-- Every factual claim in an event, allegation verdict, or red flag points back
-- to one or more blocks. This table makes citations queryable: "find all claims
-- that cite block X" or "verify quote Y exists in block Z."
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS citations (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    -- What entity owns this citation. Polymorphic — source_type disambiguates.
    source_type     TEXT NOT NULL CHECK (source_type IN (
                        'event', 'allegation_claim', 'red_flag', 'timeline_entry'
                    )),
    source_id       INTEGER NOT NULL,                                 -- FK to the entity, enforced by application
    -- What block is being cited
    block_id        INTEGER REFERENCES blocks(id) ON DELETE RESTRICT NOT NULL,
    -- The exact quoted text from the block. Verifiable via ILIKE against blocks.text_content.
    quote           TEXT,
    -- Convenience denormalization — avoids joining blocks for page number
    page            INTEGER,
    -- When this citation was created (for audit trail)
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_citations_source ON citations (source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_citations_block ON citations (block_id);
CREATE INDEX IF NOT EXISTS idx_citations_case ON citations (case_id);

-- ============================================================================
-- EVENTS — Extracted timeline entries.
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    workspace_id    INTEGER,                                          -- deferred: FK to workspaces
    -- When did this happen?
    event_at        TIMESTAMPTZ,                                      -- precise time if known
    event_date      DATE,                                             -- at minimum, a date
    -- Ordering within same-day events
    sequence_hint   INTEGER DEFAULT 0,
    -- Who acted?
    actor           TEXT,                                             -- name at the time of the event
    actor_id        INTEGER REFERENCES parties(id) ON DELETE SET NULL, -- resolved to a known party
    -- What happened?
    kind            TEXT NOT NULL CHECK (kind IN (
                        'finding', 'decision', 'intervention', 'result',
                        'transition', 'communication', 'observation',
                        'other'
                    )),
    summary         TEXT NOT NULL,                                    -- one-sentence description
    -- Provenance
    source          TEXT NOT NULL DEFAULT 'agent' CHECK (source IN ('user', 'agent')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_case ON events (case_id);
CREATE INDEX IF NOT EXISTS idx_events_workspace ON events (workspace_id);
CREATE INDEX IF NOT EXISTS idx_events_date ON events (case_id, event_date, sequence_hint);
CREATE INDEX IF NOT EXISTS idx_events_actor ON events (actor_id);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events (kind);

-- ============================================================================
-- WORKSPACES — Deferred but schema-supported from day one.
-- ============================================================================
CREATE TABLE IF NOT EXISTS workspaces (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,                                    -- "Motion to Dismiss" or "Expert Review"
    phase           TEXT CHECK (phase IN (
                        'intake', 'motion_to_dismiss', 'discovery',
                        'summary_judgment', 'trial_prep', 'appeal',
                        'initial_screening', 'expert_review', 'hearing_prep',
                        'drafting', 'revision', 'other'
                    )),
    description     TEXT,
    parent_id       INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    status          TEXT DEFAULT 'active' CHECK (status IN (
                        'active', 'complete', 'archived'
                    )),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (case_id, name)
);

CREATE INDEX IF NOT EXISTS idx_workspaces_case ON workspaces (case_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_parent ON workspaces (parent_id);

-- Add FK references now that workspaces exists.
-- DO blocks used instead of ADD CONSTRAINT IF NOT EXISTS for PG 14 compatibility.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_documents_workspace'
          AND conrelid = 'documents'::regclass
    ) THEN
        ALTER TABLE documents
            ADD CONSTRAINT fk_documents_workspace
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_events_workspace'
          AND conrelid = 'events'::regclass
    ) THEN
        ALTER TABLE events
            ADD CONSTRAINT fk_events_workspace
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- USERS — Authentication accounts.
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- ============================================================================
-- EMBEDDING CACHE — Avoid re-embedding identical text.
-- ============================================================================
CREATE TABLE IF NOT EXISTS embedding_cache (
    content_hash    TEXT PRIMARY KEY,                                 -- sha256 of the text
    embedding       VECTOR(1024) NOT NULL,
    model           TEXT NOT NULL,                                    -- e.g. "mistral-embed"
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- JOBS — Background ingestion / processing queue.
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER NOT NULL,
    job_type        TEXT NOT NULL CHECK (job_type IN (
                        'ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                        'analyze', 'export', 'ocr', 'embed', 'enrich', 'other'
                    )),
    status          TEXT NOT NULL DEFAULT 'queued' CHECK (
                        status IN ('queued', 'processing', 'complete', 'failed')
                    ),
    storage_ref     JSONB,
    progress_pct    INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 0,
    document_id     INTEGER,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_case ON jobs (case_id);

-- ============================================================================
-- AGENT WORKSPACE PERMISSIONS
-- ============================================================================
-- The agent_work schema is where the agent creates temp tables, views, and
-- working state. It has full write access to agent_work, read-only access
-- to vision (via the application layer — the DB user has read access to
-- vision tables).

-- Revoke write access to vision schema from the application role.
-- Grant full access to agent_work schema.
-- (Uncomment and replace 'app_role' with the actual role name.)
--
-- REVOKE ALL ON SCHEMA vision FROM app_role;
-- GRANT USAGE ON SCHEMA vision TO app_role;
-- GRANT SELECT ON ALL TABLES IN SCHEMA vision TO app_role;
-- GRANT ALL ON SCHEMA agent_work TO app_role;

-- ============================================================================
-- MIGRATIONS TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    applied_at      TIMESTAMPTZ DEFAULT now()
);

INSERT INTO schema_migrations (version, name) VALUES (1, 'initial_schema')
ON CONFLICT (version) DO NOTHING;

-- Add enrich job type (migration v2). The CREATE TABLE above has the new
-- constraint for fresh installs; this block updates existing databases.
DO $$
BEGIN
    ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
    ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
        CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                             'analyze', 'export', 'ocr', 'embed', 'enrich', 'other'));
END $$;

INSERT INTO schema_migrations (version, name) VALUES (2, 'add_enrich_job_type')
ON CONFLICT (version) DO NOTHING;
