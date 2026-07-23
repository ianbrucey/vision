#!/usr/bin/env python3
"""Vision — Publog FLIS PostgreSQL Loader.

Loads Decomp.exe pipe-delimited exports into PostgreSQL using the
vision-api container (which has psycopg2 and DB network access).

Usage (on server):
    ssh vision
    docker cp load_publog_loader.py vision-new-vision-api-1:/app/
    docker cp publog_data/ vision-new-vision-api-1:/app/publog_data/
    docker compose exec vision-api python3 /app/publog_loader.py
"""
import gzip, os, sys, io
from pathlib import Path

import psycopg2
from psycopg2 import sql

DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app/publog_data")

# DB connection (inside Docker network)
CONN = psycopg2.connect(
    host=os.environ.get("VISION_DB_HOST", "vision-db"),
    port=os.environ.get("VISION_DB_PORT", "5432"),
    dbname=os.environ.get("VISION_DB_DATABASE", "vision"),
    user=os.environ.get("VISION_DB_USERNAME", "vision"),
    password=os.environ.get("VISION_DB_PASSWORD", "vision_dev"),
)
CONN.autocommit = True

# Map export file prefix → DB table
# Format: (table_name, column_mapping_dict)
# column_mapping_dict: {export_column_lower: db_column_name}
TABLES = {
    "publog_flis_nsn": {
        "table": "vision.publog_flis_nsn",
        "map": {
            "fsc": "fsc", "niin": "niin", "inc": "inc",
            "item_name": "item_name", "sos": "sos",
            "end_item_name": "end_item_name",
            "cancelled_niin": "cancelled_niin",
        }
    },
    "publog_flis_management": {
        "table": "vision.publog_flis_management",
        "map": {
            "niin": "niin", "effective_date": "effective_date",
            "moe": "moe", "aac": "aac", "sos": "sos", "sosm": "sosm",
            "ui": "ui", "ui_conv_fac": "ui_conv_fac",
            "unit_price": "unit_price", "qup": "qup",
            "ciic": "ciic", "slc": "slc",
            "rep_rec_code": "rep_rec_code",
            "mgmt_ctl": "mgmt_ctl",
            "rep_net_pr": "rep_net_pr", "usc": "usc",
            # row_obs_dt is in the file but we skip it
        }
    },
    "publog_flis_identification": {
        "table": "vision.publog_flis_identification",
        "map": {
            "niin": "niin", "ii": "ii", "iuid_indicator": "iuid_indicator",
            "esd_emi": "esd_emi", "hmic": "hmic", "fedmall": "fedmall",
            "rpd_mrc": "rpd_mrc", "pmic": "pmic",
            "dmil_int_cd": "dmil_int_cd", "crit_cd": "crit_cd",
            "dmil": "dmil", "adp": "adp", "enac": "enac",
            "hcc": "hcc", "lst_kwn_sos": "lst_kwn_sos",
            "schedule_b": "schedule_b", "inc": "inc",
            "niin_asgmt": "niin_asgmt", "pinc": "pinc",
        }
    },
    "publog_moe_rule": {
        "table": "vision.publog_moe_rule",
        "map": {
            "niin": "niin", "moe_rl": "moe_rl",
            "moe_cd": "moe_cd", "amc": "amc", "amsc": "amsc",
            "nimsc": "nimsc", "dt_asgnd": "dt_asgnd",
            "imc": "imc", "imca": "imca", "aac": "aac",
            "pica": "pica", "pica_loa": "pica_loa",
            "sica": "sica", "sica_loa": "sica_loa",
            "auth_collab": "auth_collab", "supp_collab": "supp_collab",
            "dsor": "dsor", "fmr_moe_rl": "fmr_moe_rl",
            # row_obs_dt in file but skipped
        }
    },
    "publog_cage": {
        "table": "vision.publog_cage",
        "map": {
            "cage_code": "cage_code", "cage_status": "cage_status",
            "type": "type", "cao": "cao", "company": "company",
            "city": "city", "state_province": "state_province",
            "zip_postal_zone": "zip_postal_zone", "country": "country",
        }
    },
    "publog_flis_part": {
        "table": "vision.publog_flis_part",
        "map": {
            "niin": "niin", "cage_status": "cage_status",
            "medals": "medals", "rnvc": "rnvc", "rnjc": "rnjc",
            "rnfc": "rnfc", "rnsc": "rnsc", "rncc": "rncc",
            "dac": "dac", "hcc": "hcc", "sadc": "sadc",
            "rnaac": "rnaac", "msds": "msds",
            "cage_code": "cage_code", "part_number": "part_number",
        }
    },
}


def load_table(gzfile: Path, config: dict) -> int:
    """Load one gzipped file — maps columns and uses COPY."""
    table = config["table"]
    col_map = config["map"]

    if not gzfile.exists():
        print(f"  SKIP: {gzfile} not found")
        return 0

    size_mb = gzfile.stat().st_size / 1024 / 1024
    print(f"  Reading {gzfile.name} ({size_mb:.0f}MB)...")

    # Read header
    with gzip.open(gzfile, "rt", encoding="utf-8", errors="replace") as f:
        header_line = f.readline().strip()
    file_cols = [c.strip().lower() for c in header_line.split("|")]

    # Build mapping: file column index → DB column name
    col_indices = []
    db_cols = []
    skipped = []
    for fc in file_cols:
        if fc in col_map:
            col_indices.append(file_cols.index(fc))
            db_cols.append(col_map[fc])
        else:
            skipped.append(fc)

    if skipped:
        print(f"    Skipping columns: {skipped}")
    print(f"    Loading {len(db_cols)} columns: {', '.join(db_cols[:8])}...")

    # Truncate (in a transaction)
    with CONN.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")

    # Build data rows — filter to only mapped columns in file order
    buf = io.StringIO()
    total = 0
    batch_size = 250000
    batch_count = 0

    with gzip.open(gzfile, "rt", encoding="utf-8", errors="replace") as f:
        next(f)  # skip header
        for line in f:
            fields = line.strip().split("|")
            # Select only mapped columns, in file order
            mapped = [fields[i] if i < len(fields) else "" for i in range(len(file_cols)) if file_cols[i] in col_map]
            buf.write("\t".join(mapped) + "\n")
            total += 1

            if total % batch_size == 0:
                buf.seek(0)
                with CONN.cursor() as cur:
                    cols_sql = sql.SQL(", ").join([sql.Identifier(c) for c in db_cols])
                    copy_sql = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t')").format(
                        sql.SQL(table), cols_sql
                    )
                    cur.copy_expert(copy_sql, buf)
                    CONN.commit()
                batch_count += 1
                print(f"    ... {total:,} rows ({batch_count * batch_size / 1_000_000:.1f}M)", flush=True)
                buf = io.StringIO()

    # Final batch
    if buf.tell() > 0:
        buf.seek(0)
        with CONN.cursor() as cur:
            cols_sql = sql.SQL(", ").join([sql.Identifier(c) for c in db_cols])
            copy_sql = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t')").format(
                sql.SQL(table), cols_sql
            )
            cur.copy_expert(copy_sql, buf)
            CONN.commit()

    # Verify
    with CONN.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]

    print(f"  → {count:,} rows loaded")
    return count


def main():
    print("=" * 60)
    print("Publog FLIS Loader")
    print(f"Data dir: {DATA_DIR}")
    print("=" * 60)
    print()

    for prefix, config in TABLES.items():
        gzfile = DATA_DIR / f"{prefix}.txt.gz"
        print(f"[{prefix}]")
        try:
            load_table(gzfile, config)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
        print()

    # Final summary
    print("=" * 60)
    print("FINAL COUNTS")
    print("=" * 60)
    with CONN.cursor() as cur:
        for prefix, config in TABLES.items():
            cur.execute(f"SELECT COUNT(*) FROM {config['table']}")
            count = cur.fetchone()[0]
            print(f"  {config['table']:40s} {count:>14,} rows")
    print("=" * 60)
    print("Done.")
    CONN.close()


if __name__ == "__main__":
    main()
