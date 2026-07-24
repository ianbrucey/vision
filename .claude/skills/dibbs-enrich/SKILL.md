# DIBBS Enrich Skill

Enrich a batch of DIBBS solicitations with FLIS data (item name, pricing, AMC/AMSC competability, DMIL/HMIC flags) and match approved-source CAGE codes against known vendors.

## Input

Drop files into `dibbs/inbox/`. Three formats are supported:

| Format | Detection | Example |
|---|---|---|
| **Email notification** | Lines containing `dibbs.bsm.dla.mil/RFQ/RFQRec.aspx?sn=` | `https://...?sn=SPE3SE26T1057 4110013669648 21GM9` |
| **Batch quote (BQ)** | CSV with 121+ columns, no header row, solicitation in column 0, NSN in column 46 | `bq260723.txt` |
| **Approved source (AS)** | CSV with 4 columns: NSN, CAGE, PartNumber, empty | `as260723.txt` |

The agent detects format automatically by reading the first few lines.

## Protocol

Run every step via `ssh vision "docker compose -f /root/vision-new/docker-compose.prod.yml exec -T vision-db psql -U vision -d vision"` piping SQL through stdin. All tables are in the `vision` schema.

---

### Step 1: Parse inbox → extract unique NSNs

For each file in `dibbs/inbox/`:

**Email format** — regex each line:
```
https://www\.dibbs\.bsm\.dla\.mil/RFQ/RFQRec\.aspx\?sn=(\S+)\s+(\d{13})
```
→ capture group 1 = solicitation, group 2 = full NSN (FSC+NIIN, 13 digits). Split NSN into `fsc` (first 4) and `niin` (last 9).

**BQ format** — read with Python `csv.reader`, no header:
- Column 0 = solicitation
- Column 45 = purchase request number
- Column 46 = NSN (13-digit FSC+NIIN packed)
- Column 47 = unit of issue
- Column 48 = quantity
- Column 49 = delivery days (unreliable — use 90 as default)

**AS format** — read with Python `csv.reader`:
- Column 0 = NSN (may be 13-digit packed or dash-separated)
- Column 1 = CAGE code
- Column 2 = part number

Collect all unique NSNs (niin = last 9 chars, fsc = first 4 chars) into a list. Also build a `solicitation → {nsn, qty, due_date, pr}` map from BQ+email sources.

---

### Step 2: Enrich NSNs — item name, INC, cancelled status

For the full list of unique NIINs, build an IN clause and run:

```sql
SELECT fsc, niin, inc, item_name, sos, cancelled_niin
FROM vision.publog_flis_nsn
WHERE niin IN ('014532373','013146694', ...);
```

Map results back to each NSN. If `cancelled_niin` is non-empty, the NSN has been replaced — flag it.

---

### Step 3: Competability — AMC/AMSC

AMC tells you if you can bid. Run this query with the same NIIN list:

```sql
SELECT DISTINCT ON (niin) niin, amc, amsc, moe_cd, aac
FROM vision.publog_moe_rule
WHERE niin IN (...);
```

Interpretation:
- **AMC 0** = Full and open competition — **you can bid**
- **AMC 1** = Suitable for competitive acquisition, restrictive terms apply
- **AMC 2** = Restricted to approved sources
- **AMC 3** = Acquire directly from actual manufacturer only — **sole source**
- **AMC 4** = Acquire from approved source — restricted
- **AMC 5** = Acquire from approved source, no alternate — **very restricted**
- **NULL/empty** = No MOE rule exists — check AAC instead

If no AMC record: check AAC from the management table:
```sql
SELECT DISTINCT ON (niin) niin, aac
FROM vision.publog_flis_management
WHERE niin IN (...);
```
- AAC **V** or **Z** = vendors/suppliers can provide — likely competable
- AAC **L** or **D** = restricted — harder to break into

Flag each NSN as `competable=true/false/unknown`.

---

### Step 4: Pricing — historical unit price

```sql
SELECT DISTINCT ON (niin) niin, unit_price, ui, slc, ciic
FROM vision.publog_flis_management
WHERE niin IN (...) AND unit_price IS NOT NULL AND unit_price != ''
ORDER BY niin, effective_date DESC;
```

Format `unit_price` — it comes as zero-padded string like `000003228.01`. Strip leading zeros, treat as dollars. Some NSNs have multiple MOE records with the same price; `DISTINCT ON (niin)` gets one per NSN.

---

### Step 5: Restrictions — DMIL, HMIC, criticality

```sql
SELECT niin, dmil, hmic, hcc, crit_cd, schedule_b, iuid_indicator
FROM vision.publog_flis_identification
WHERE niin IN (...);
```

Key flags:
- **DMIL** = Demilitarization code. A, B, Q = requires demil (extra compliance). C, D, G = no demil required.
- **HMIC** = Hazardous material. N = none. Y, D, H = hazmat flag — may need special handling.
- **CRIT_CD** = Criticality. X = critical safety item. Not X = standard.

---

### Step 6: Approved sources — CAGE codes

If an AS file was in the inbox, use those CAGE→NSN mappings directly. Otherwise, query Publog:

```sql
SELECT niin, part_number, cage_code, rncc, rnvc, dac
FROM vision.publog_flis_part
WHERE niin IN (...)
  AND rncc IN ('1','2','3','7')  -- only valid/authoritative references
ORDER BY niin, rncc;
```

RNCC codes: 1=authoritative, 2=valid reference, 3=design control, 7=vendor item. Skip 5 (obsolete), 8 (cancelled).

---

### Step 7: Vendor matching — contact info

For all CAGE codes found (both from AS file and Publog part table), look up vendors:

```sql
SELECT cage_code, vendor_name, contact_name, contact_email, contact_phone,
       website, address_line1, city, state, zipcode,
       is_small_business, is_woman_owned, is_veteran_owned, is_sdvosb,
       is_hubzone, is_8a, naics_code_primary, capabilities
FROM vision.vendors
WHERE cage_code IN ('0BT64','064S4',...);
```

Also enrich CAGE codes with company names from Publog (even if no vendor match):

```sql
SELECT cage_code, company, city, state_province, country, cage_status
FROM vision.publog_cage
WHERE cage_code IN (...);
```

Join vendor contacts + Publog company names on `cage_code`. A CAGE may have a Publog entry (company name, location) but no vendor record (no contact info). Flag as `in_vendor_db=true/false`.

---

### Step 8: Assemble output CSV

Write to `dibbs/outbox/<date>_enriched.csv`. Columns:

```
nsn, fsc, niin, nomenclature, inc, sos,
cancelled, cancelled_niin,
amc, amsc, aac, competable, competability_notes,
unit_price, ui, slc, ciic,
dmil, hmic, hcc, crit_cd,
approved_cage, approved_part, rncc,
cage_company, cage_city, cage_state,
vendor_name, contact_name, contact_email, contact_phone, website,
is_small_business, is_woman_owned, is_veteran_owned,
delivery_days, qty, due_date, solicitation, purchase_request,
source_file
```

One row per NSN–solicitation pair. If a solicitation has quantity/due date from BQ/email, include those. If from AS-only (no solicitation), those fields are blank.

### Output usage guide

1. **Filter `competable = true`** → bid-eligible items
2. **Sort by `unit_price DESC`** → highest value first
3. **Filter `in_vendor_db = true` AND `contact_email != ''`** → ready to email for quotes
4. **For `approved_cage` filled but `vendor_name` empty** → your prospecting list. Look up the CAGE on SAM.gov or Google the company name to find contact info.
5. **One CAGE often maps to many NSNs** → group by approved_cage to see clusters. One supplier relationship unlocks multiple line items.

---

## Execution notes for the agent

- All queries run against the remote server via `ssh vision "docker compose -f /root/vision-new/docker-compose.prod.yml exec -T vision-db psql -U vision -d vision"`.
- Pipe SQL via heredoc or stdin. Use `-t -A -F '|'` flags for machine-parseable output when doing bulk extraction: `psql -U vision -d vision -t -A -F '|' -c "SELECT ..."`.
- The IN clause max is ~32k parameters. If inbox has more than ~5k unique NSNs, batch them in groups of 2000.
- NSNs from email are 13-digit packed (FSC+NIIN). Split to `fsc=nsn[:4]`, `niin=nsn[4:]`.
- The BQ file has no header. Column positions are fixed by DIBBS specification — column 0 is always solicitation, column 46 is always NSN.
- Output file goes to `dibbs/outbox/YYYY-MM-DD_enriched.csv`. Process inbox files oldest-first.
