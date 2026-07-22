-- 022_vendor_outreach_received_status.sql
-- Allow 'received' status on vendor_outreach_messages so inbound replies
-- are not confused with editable drafts in the frontend thread UI.
ALTER TABLE vision.vendor_outreach_messages
  DROP CONSTRAINT IF EXISTS vendor_outreach_messages_status_check;

ALTER TABLE vision.vendor_outreach_messages
  ADD CONSTRAINT vendor_outreach_messages_status_check
  CHECK (status IN ('draft', 'sent', 'failed', 'received'));

INSERT INTO vision.schema_migrations (version, name)
VALUES (31, 'vendor_outreach_received_status')
ON CONFLICT (version) DO NOTHING;
