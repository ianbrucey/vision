"""
Test the pipeline filter logic against the actual SAM databank CSV data.
Runs against sourcing.db (SQLite) — no API server needed.
"""

import sqlite3
from datetime import date, datetime
from collections import defaultdict

# ---------------------------------------------------------------------------
# Filter constants — MUST MATCH backend/core/pipeline.py
# ---------------------------------------------------------------------------

_EXCLUDED_TYPES = {
    "Award Notice",
    "Justification",
    "Sale of Surplus Property",
}

_INCLUDED_TYPES = {
    "Combined Synopsis/Solicitation",
    "Solicitation",
    "Presolicitation",
    "Sources Sought",
    # "Special Notice",
    # "Consolidate/(Substantially) Bundle",
}

_CONSTRUCTION_KW = [
    "Construction", "Building", "Plumbing", "HVAC",
    "Electrical Contractors", "Carpentry", "Masonry", "Roofing",
    "Concrete", "Painting", "Welding", "Excavation", "Demolition",
    "Flooring", "Drywall", "Fencing", "Paving", "Structural Steel",
    "Fire Protection", "Elevator", "Asphalt", "Sheet Metal",
    "Finishing Contractors", "Power and Communication Line",
    "Water and Sewer Line", "Highway, Street, and Bridge",
    "Industrial Building",
]

_CONSTRUCTION_EXCLUDES = {
    "Ship Building", "Machinery Manufacturing",
    "Equipment Manufacturing", "Mining", "Equipment Rental",
    "Equipment Merchant", "Sand and Gravel",
    "Prefabricated Metal Building", "Construction Machinery",
}

_FACILITIES_KW = [
    "Facilities Support", "Janitorial", "Custodial", "Landscaping",
    "Grounds", "Security Guards", "Security Systems",
    "Waste Collection", "Waste Treatment", "Pest Control",
    "Laundry", "Food Service", "Cafeteria",
]

_IT_KW = [
    "Software", "Computer Programming", "Computer Systems Design",
    "Electronic Computer", "Computing Infrastructure",
    "Data Processing", "Custom Computer", "Cloud", "Cybersecurity",
    "Information Technology", "Telecom", "Wireless", "Satellite", "Internet",
]

_SB_SET_ASIDE_KW = [
    "Total Small Business", "Service-Disabled Veteran-Owned Small Business",
    "SDVOSB", "Historically Underutilized Business", "HUBZone", "8(a)",
    "SBA Certified Women-Owned Small Business", "WOSB",
    "Women-Owned Small Business", "EDWOSB", "Economically Disadvantaged WOSB",
    "Indian Small Business Economic Enterprise", "ISBEE",
    "Indian Economic Enterprise", "IEE", "Veteran-Owned Small Business",
    "Buy Indian", "Local Area Set-Aside",
]

_EXCLUDED_SET_ASIDE_KW = ["Partial Small Business"]


# ---------------------------------------------------------------------------
# Classification functions — MUST MATCH backend/core/pipeline.py
# ---------------------------------------------------------------------------

def classify_naics(naics_description):
    if not naics_description:
        return "other"
    naics_lower = naics_description.lower()
    for kw in _CONSTRUCTION_EXCLUDES:
        if kw.lower() in naics_lower:
            return "other"
    for kw in _CONSTRUCTION_KW:
        if kw.lower() in naics_lower:
            return "construction"
    for kw in _IT_KW:
        if kw.lower() in naics_lower:
            return "it"
    for kw in _FACILITIES_KW:
        if kw.lower() in naics_lower:
            return "facilities"
    return "other"


def classify_set_aside(set_aside):
    if not set_aside or not set_aside.strip():
        return "full_and_open"
    for kw in _EXCLUDED_SET_ASIDE_KW:
        if kw.lower() in set_aside.lower():
            return "partial_set_aside"
    for kw in _SB_SET_ASIDE_KW:
        if kw.lower() in set_aside.lower():
            return "sb_set_aside"
    return "full_and_open"


def parse_date(date_str):
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in [
        "%b %d, %Y %I:%M %p UTC",
        "%b %d, %Y %I:%M %p",
        "%Y-%m-%d", "%m/%d/%Y",
    ]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def bucket_urgency(response_date_str, opportunity_type=None):
    if opportunity_type == "Sources Sought":
        return "red"
    dt = parse_date(response_date_str)
    if dt is None:
        return "unknown"
    days = (dt.date() - date.today()).days
    if days < 0:
        return "past_due"
    if days <= 7:
        return "red"
    if days <= 14:
        return "yellow"
    return "green"


def is_sources_sought_recently_closed(response_date_str):
    dt = parse_date(response_date_str)
    if dt is None:
        return False
    days_since_close = (date.today() - dt.date()).days
    return 0 <= days_since_close <= 30


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def main():
    db = sqlite3.connect("sourcing.db")
    cur = db.cursor()

    cur.execute("""
        SELECT "Notice ID", "Contract Opportunity Type",
               NAICS, "Current Set Aside", "Current Response Date",
               "Opportunity Title"
        FROM sam_opportunities
    """)
    rows = cur.fetchall()
    db.close()

    results = {
        "total": len(rows),
        "queued": 0,
        "skipped": 0,
        "skipped_breakdown": defaultdict(int),
        "queued_by_category": defaultdict(int),
        "queued_by_urgency": defaultdict(int),
        "queued_examples": [],
    }

    print(f"Testing {len(rows)} rows against filter logic...\n")

    for notice_id, opp_type, naics_desc, set_aside, response_date, title in rows:
        # Gate 1: Type
        if opp_type in _EXCLUDED_TYPES or (
            opp_type and opp_type not in _INCLUDED_TYPES
        ):
            results["skipped"] += 1
            results["skipped_breakdown"]["excluded_type"] += 1
            continue

        # Gate 2: NAICS
        category = classify_naics(naics_desc)
        if category == "other":
            results["skipped"] += 1
            results["skipped_breakdown"]["wrong_naics"] += 1
            continue

        # Gate 3: Set-aside
        sa_group = classify_set_aside(set_aside)
        if sa_group == "full_and_open":
            results["skipped"] += 1
            results["skipped_breakdown"]["full_and_open"] += 1
            continue
        if sa_group == "partial_set_aside":
            results["skipped"] += 1
            results["skipped_breakdown"]["partial_set_aside"] += 1
            continue

        # Gate 4: Urgency
        urgency = bucket_urgency(response_date, opp_type)
        if urgency == "past_due":
            if opp_type == "Sources Sought" and is_sources_sought_recently_closed(response_date):
                urgency = "red"
            else:
                results["skipped"] += 1
                results["skipped_breakdown"]["past_due"] += 1
                continue

        # Gate 5: Notice ID validity
        if not notice_id or len((notice_id or "").strip()) < 8:
            results["skipped"] += 1
            results["skipped_breakdown"]["invalid_notice_id"] += 1
            continue

        # Passed all gates
        results["queued"] += 1
        results["queued_by_category"][category] += 1
        results["queued_by_urgency"][urgency] += 1
        if len(results["queued_examples"]) < 10:
            results["queued_examples"].append({
                "notice_id": notice_id,
                "title": title[:80] if title else "",
                "category": category,
                "type": opp_type,
                "urgency": urgency,
            })

    print("=" * 60)
    print(f"Total rows:           {results['total']:>6}")
    print(f"Queued (pass filter): {results['queued']:>6}")
    print(f"Skipped:              {results['skipped']:>6}")
    print("\nSkipped breakdown:")
    for reason, count in sorted(results["skipped_breakdown"].items(), key=lambda x: -x[1]):
        print(f"  {reason:<25} {count:>6}")
    print(f"\nQueued by category:")
    for cat, count in sorted(results["queued_by_category"].items(), key=lambda x: -x[1]):
        print(f"  {cat:<25} {count:>6}")
    print(f"\nQueued by urgency:")
    for urg, count in sorted(results["queued_by_urgency"].items(), key=lambda x: -x[1]):
        print(f"  {urg:<25} {count:>6}")
    print(f"\nSample queued notices:")
    for ex in results["queued_examples"]:
        print(f"  [{ex['category']}][{ex['urgency']}] {ex['notice_id']}: {ex['title']}")

    return results


if __name__ == "__main__":
    main()
