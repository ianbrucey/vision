-- 031: Drop the old role check constraint and re-add with 'vendor'.

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;

-- Re-add with vendor role allowed
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IN ('user', 'admin', 'vendor'));
