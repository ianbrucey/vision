-- 023_inbound_read_at.sql
-- Track when inbound vendor replies are read so the UI can show
-- unread counts and notification badges.
ALTER TABLE vision.vendor_outreach_messages
  ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;

INSERT INTO vision.schema_migrations (version, name)
VALUES (32, 'inbound_read_at')
ON CONFLICT (version) DO NOTHING;
