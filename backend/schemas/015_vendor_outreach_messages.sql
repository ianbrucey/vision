-- ============================================================================
-- Vision — Vendor Outreach Messages Migration v24
-- ============================================================================
-- One row per message (outbound draft/sent, or inbound reply) in a vendor
-- match's outreach thread. Replaces the one-shot outreach_message_id/
-- outreach_reply_token columns added to vendor_matches in v23 (014) as the
-- system of record for send state — those columns remain on vendor_matches
-- for now (still written by mark_email_sent for backward-compat/rollup
-- convenience) but are no longer the only place a send is tracked.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS vendor_outreach_messages (
    id                  SERIAL PRIMARY KEY,
    vendor_match_id     INTEGER REFERENCES vendor_matches(id) ON DELETE CASCADE NOT NULL,
    direction           TEXT NOT NULL CHECK (direction IN ('outbound', 'inbound')),
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'failed')),
    subject             TEXT NOT NULL,
    body                TEXT NOT NULL,
    mailgun_message_id  TEXT,
    reply_token         TEXT,
    document_id         INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    sent_at             TIMESTAMPTZ,
    received_at         TIMESTAMPTZ,
    error_message       TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outreach_messages_match
    ON vendor_outreach_messages (vendor_match_id, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_messages_reply_token
    ON vendor_outreach_messages (reply_token) WHERE reply_token IS NOT NULL;

INSERT INTO schema_migrations (version, name) VALUES (24, 'vendor_outreach_messages')
ON CONFLICT (version) DO NOTHING;
