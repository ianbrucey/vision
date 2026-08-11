-- 028: Add assignee tracking to solicitations.
-- Users can claim/release solicitations; admin can reassign.

ALTER TABLE solicitations
  ADD COLUMN IF NOT EXISTS assignee_id uuid REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS assigned_at timestamptz;
