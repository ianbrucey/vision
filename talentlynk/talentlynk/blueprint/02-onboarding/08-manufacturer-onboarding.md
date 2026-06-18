# Manufacturer Onboarding

## Purpose
Intake flow for small U.S.-based domestic manufacturers — factories and fabricators producing physical goods — who form the "American Alibaba" product supply layer of the network.

## What Makes This Different from Service Vendor Onboarding

Product acquisition has a completely different regulatory playbook. Under the Non-Manufacturer Rule (NMR), only **actual manufacturers** (not dealers/distributors) can supply products for small business set-aside contracts. The onboarding flow must verify manufacturing status.

## Inputs
- Company identity, location, years in operation
- Proof of manufacturing: facility address, equipment, production capacity
- Product catalog with categories and specifications
- NAICS manufacturing codes (31-33 series)
- Unit pricing and minimum order quantities
- Production lead times
- Shipping capabilities
- Buy American Act compliance status (country of origin)
- Small business certifications

## Outputs
- Manufacturer profile in database
- Product catalog stored and searchable
- NAICS manufacturing codes tagged
- NMR compliance flag: verified manufacturer (not dealer)
- BAA compliance flag

## Onboarding Flow

### Step 1: Company & Facility Verification
- Legal name, address
- Manufacturing facility location(s)
- Years in operation
- Upload: business license, facility photos/evidence

### Step 2: Product Catalog
- Product categories (from taxonomy)
- Individual product entries with specs
- Unit pricing (bulk tiers if applicable)
- Minimum order quantities
- Standard lead times

### Step 3: Manufacturing Verification (Critical for NMR)
- Self-declaration: "Do you physically manufacture these products in your own facility?"
- Evidence: equipment list, production capacity, raw material sourcing
- **System flag:** If dealer/distributor only → restricted to Full & Open or Class-Waived contracts only

### Step 4: Compliance & Certifications
- Small business certifications
- ISO or industry-specific quality certs
- Buy American Act: country of origin for products
- Berry Amendment compliance (if textiles/apparel)

### Step 5: Pricing & Terms
- Standard pricing (per unit, volume tiers)
- Net terms offered
- Shipping terms (FOB origin vs. destination)
- Capacity: max units per month

### Step 6: Agreement Signing
- [[../03-agreements/master-teaming-agreement]] (for set-aside bidding)
- Or: commercial PO terms only (for Full & Open)
- Profile enters network database

## Dependencies
- [[../11-product-acquisition/non-manufacturer-rule]]
- [[../11-product-acquisition/small-manufacturer-directory]]
- [[../11-product-acquisition/buy-american-act]]
- [[../03-agreements/master-teaming-agreement]]

## Key Rules & Compliance
- Non-Manufacturer Rule (13 CFR § 121.406): products under small business set-asides must come from domestic small business manufacturers
- Dealer Trap: a certified small business that's only a distributor does NOT satisfy NMR
- Buy American Act: certain contracts require U.S.-origin products
- Berry Amendment: DoD textile/food contracts require 100% U.S. origin

## Open Questions
- How to verify "actual manufacturer" status beyond self-declaration?
- On-site visit verification for high-value manufacturing partners?
