-- 01-schema.sql — Migration 032: Vendor Teaming Agreements + case-less documents
-- Spec artifact for vendor-onboarding (Ticket 0). Applied via
-- ensure_vendor_agreements_schema() in core/db.py at API startup.

-- Allow case-less documents (signed MTA PDFs now; vendor compliance
-- uploads next). UNIQUE (case_id, name) treats NULLs as distinct, so
-- multiple case-less documents may share a name — intended.
ALTER TABLE documents ALTER COLUMN case_id DROP NOT NULL;

-- Vendor-owned documents: extend the owner model (case_id | talent_id)
-- with vendor_user_id so signed agreements have a real owner row.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS vendor_user_id uuid REFERENCES users(id);
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_owner_check;
ALTER TABLE documents ADD CONSTRAINT documents_owner_check
    CHECK (case_id IS NOT NULL OR talent_id IS NOT NULL OR vendor_user_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_documents_vendor_user ON documents(vendor_user_id);

CREATE TABLE IF NOT EXISTS vendor_teaming_agreements (
    id                      serial PRIMARY KEY,
    agreement_type          text NOT NULL CHECK (agreement_type IN ('mta', 'bsta', 'subcontract')),
    vendor_user_id          uuid NOT NULL REFERENCES users(id),
    solicitation_id         integer REFERENCES solicitations(id),   -- NULL for MTA
    document_id             integer REFERENCES documents(id),       -- signed PDF

    -- BSTA / subcontract fields (unused by MTA)
    naics_code              text,
    set_aside_type          text CHECK (set_aside_type IN ('sb', 'wosb', 'sdvosb', 'hubzone', '8a', 'other')),
    contract_type           text CHECK (contract_type IN ('services', 'supplies', 'gen_construction', 'specialty_construction')),
    estimated_value         numeric(14,2),
    workshare_pct           numeric(5,2),

    -- Computed compliance fields (unused by MTA)
    los_applicable          boolean,
    los_check_passed        boolean,
    similarly_situated      boolean,
    similarly_situated_cert boolean,

    -- E-signature audit trail
    signed_name             text,
    signed_title            text,
    signed_ip               inet,
    signed_user_agent       text,
    content_hash            text,        -- sha256 of signed PDF bytes (render pass 1)
    template_version        text,        -- MTA template version constant at signing

    -- Status tracking
    status                  text NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft', 'pending_signature', 'executed', 'terminated')),
    executed_at             timestamptz,
    expires_at              timestamptz, -- executed_at + 2 years (MTA Art. 8.1; informational this build)
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vta_vendor ON vendor_teaming_agreements(vendor_user_id);
CREATE INDEX IF NOT EXISTS idx_vta_solicitation ON vendor_teaming_agreements(solicitation_id);
CREATE INDEX IF NOT EXISTS idx_vta_type_status ON vendor_teaming_agreements(agreement_type, status);

-- At most one executed MTA per vendor — duplicate-sign prevention at DB level.
CREATE UNIQUE INDEX IF NOT EXISTS uq_vta_one_executed_mta
    ON vendor_teaming_agreements (vendor_user_id)
    WHERE agreement_type = 'mta' AND status = 'executed';
