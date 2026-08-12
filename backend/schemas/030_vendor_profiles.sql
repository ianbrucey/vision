-- 030: Vendor profiles for subcontractors and suppliers.
-- Each vendor user gets exactly one profile. The vendor_type determines
-- which fields are relevant:
--   individual  — solo practitioner / independent contractor
--   service     — service provider (construction, IT, consulting, etc.)
--   manufacturer — product manufacturer / equipment supplier

CREATE TABLE IF NOT EXISTS vendor_profiles (
    id              serial PRIMARY KEY,
    external_id     uuid DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id) UNIQUE,

    -- Business identity
    business_name   text NOT NULL,
    vendor_type     text NOT NULL DEFAULT 'service'
                    CHECK (vendor_type IN ('individual', 'service', 'manufacturer')),
    uei             text,
    cage_code       text,
    tax_id          text,              -- EIN / SSN (for 1099 purposes)

    -- Capabilities
    naics_codes     text[],            -- their primary NAICS codes
    capabilities    text,              -- freeform capability description
    website         text,
    phone           text,
    address_line1   text,
    address_line2   text,
    city            text,
    state           text,
    zip             text,

    -- Compliance documents (stored in documents table, linked here)
    license_doc_id          integer REFERENCES documents(id),
    bonding_doc_id          integer REFERENCES documents(id),
    insurance_doc_id        integer REFERENCES documents(id),
    certification_doc_ids   integer[],  -- references documents(id)

    -- Financial
    bonding_capacity        numeric(12,2),
    annual_revenue          numeric(12,2),
    employee_count          integer,
    years_in_business       integer,

    -- Status
    status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'active', 'suspended', 'inactive')),
    verified_at     timestamptz,

    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vendor_profiles_user ON vendor_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_type ON vendor_profiles(vendor_type);
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_status ON vendor_profiles(status);
