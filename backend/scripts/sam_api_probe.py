"""
Probe the SAM.gov v2 API to count active Total Small Business opportunities
posted since 2026-08-09. One request — totalRecords gives the count.
"""
import os
import sys
from datetime import date
import httpx
import json

API_KEY = os.environ.get("SAM_GOV_API_KEY", "")
if not API_KEY:
    print("SAM_GOV_API_KEY not set", file=sys.stderr)
    sys.exit(1)

TODAY = date.today()
FROM_DATE = date(2026, 8, 9)

params = {
    "api_key": API_KEY,
    "postedFrom": FROM_DATE.strftime("%m/%d/%Y"),
    "postedTo": TODAY.strftime("%m/%d/%Y"),
    "setAside": "SBA",
    "limit": 100,
}

print(f"Querying SAM.gov API...")
resp = httpx.get("https://api.sam.gov/opportunities/v2/search", params=params, timeout=30)
print(f"Status: {resp.status_code}")

data = resp.json()
total = data.get("totalRecords", 0)
opportunities = data.get("opportunitiesData") or []

print(f"\nTotal records available: {total:,}")
print(f"Returned in page: {len(opportunities)}")
print(f"Pages needed at limit=100: {(total + 99) // 100}")

# Sample
print(f"\n--- First 10 of {len(opportunities)} ---")
for i, op in enumerate(opportunities[:10]):
    print(f"  {i+1}. [{op.get('type','?')}] {op.get('title','')[:120]}")
    print(f"     posted={op.get('postedDate','?')}  deadline={op.get('responseDeadLine','?')}")
    print(f"     NAICS={op.get('naicsCode','?')}  set-aside={op.get('typeOfSetAsideDescription','?')}")

# Type breakdown from this page
types = {}
for op in opportunities:
    t = op.get("type", "?")
    types[t] = types.get(t, 0) + 1
print(f"\n--- Type breakdown (this page) ---")
for t, c in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

# Write full JSON response
script_dir = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(script_dir, "sam_api_probe_output.txt")
with open(out_path, "w") as f:
    f.write(f"SAM.gov API Probe — {TODAY.isoformat()}\n")
    f.write(f"Query: Total Small Business (setAside=SBA), posted {FROM_DATE} to {TODAY}\n")
    f.write(f"{'='*70}\n\n")
    f.write(f"Total records available: {total:,}\n")
    f.write(f"Returned in this page: {len(opportunities)}\n")
    f.write(f"Pages needed at limit=100: {(total + 99) // 100}\n\n")
    f.write("--- Full JSON response (first page) ---\n")
    f.write(json.dumps(data, indent=2, default=str))

print(f"\nFull JSON written to: {out_path}")
