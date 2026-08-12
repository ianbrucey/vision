-- 029: Quotes table for subcontractor quotes attached to solicitations.

CREATE TABLE IF NOT EXISTS quotes (
    id              serial PRIMARY KEY,
    external_id     uuid DEFAULT gen_random_uuid(),
    solicitation_id integer NOT NULL REFERENCES solicitations(id) ON DELETE CASCADE,
    created_by      uuid NOT NULL REFERENCES users(id),

    notes           text,
    amount          numeric(12,2),
    poc_name        text,
    poc_email       text,
    poc_phone       text,

    status          text NOT NULL DEFAULT 'draft'
                    CHECK (status IN (
                        'draft',
                        'pending_site_visit',
                        'submitted',
                        'awarded',
                        'lost'
                    )),

    document_id     integer REFERENCES documents(id),
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_quotes_solicitation ON quotes(solicitation_id);
CREATE INDEX IF NOT EXISTS idx_quotes_created_by ON quotes(created_by);
