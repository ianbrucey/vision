#!/usr/bin/env python3
"""
Vision — Triage Diagnostic & Recovery CLI.

Used by the operations team to diagnose any stalled, failed, or partial
solicitation triage runs, inspect document ingestion status, and trigger
an immediate clean re-run.

Usage:
    python backend/scripts/diagnose_triage.py --solicitation <sol_id>
    python backend/scripts/diagnose_triage.py --case <case_id>
    python backend/scripts/diagnose_triage.py --list-failed
    python backend/scripts/diagnose_triage.py --retry <sol_id>
"""

import argparse
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from core.db import connect, tx
from core.solicitation import SolicitationManager
from ingestion.jobs import enqueue


def inspect_solicitation(solicitation_id: int | None = None, case_id: int | None = None):
    conn = connect()
    try:
        with conn.cursor() as cur:
            if solicitation_id:
                cur.execute(
                    """SELECT id, case_id, title, notice_id, ingestion_status,
                              triage_status, triage_error,
                              (artifact_scope_of_work IS NOT NULL) AS has_sow,
                              (artifact_technical_requirements IS NOT NULL) AS has_tech,
                              (artifact_deliverables_timeline IS NOT NULL) AS has_deliv,
                              (artifact_evaluation_criteria IS NOT NULL) AS has_eval,
                              (artifact_submission_checklist IS NOT NULL) AS has_check,
                              has_missing_docs
                       FROM solicitations WHERE id = %s""",
                    (solicitation_id,),
                )
            else:
                cur.execute(
                    """SELECT id, case_id, title, notice_id, ingestion_status,
                              triage_status, triage_error,
                              (artifact_scope_of_work IS NOT NULL) AS has_sow,
                              (artifact_technical_requirements IS NOT NULL) AS has_tech,
                              (artifact_deliverables_timeline IS NOT NULL) AS has_deliv,
                              (artifact_evaluation_criteria IS NOT NULL) AS has_eval,
                              (artifact_submission_checklist IS NOT NULL) AS has_check,
                              has_missing_docs
                       FROM solicitations WHERE case_id = %s""",
                    (case_id,),
                )
            sol = cur.fetchone()
            if not sol:
                print(f"[!] Solicitation not found (solicitation_id={solicitation_id}, case_id={case_id})")
                return

            sid, cid, title, nid, ing_stat, tri_stat, tri_err, has_sow, has_tech, has_deliv, has_eval, has_check, has_missing = sol
            print("=" * 60)
            print(f"SOLICITATION DIAGNOSTIC: ID {sid} (Case {cid})")
            print("=" * 60)
            print(f"  Title:            {title}")
            print(f"  Notice ID:        {nid}")
            print(f"  Ingestion Status: {ing_stat} (missing_docs_flag: {has_missing})")
            print(f"  Triage Status:    {tri_stat}")
            if tri_err:
                print(f"  Triage Error:     {tri_err}")
            print(f"  Triage Artifacts:")
            print(f"    - Scope of Work:           {'YES' if has_sow else 'MISSING'}")
            print(f"    - Tech Requirements:       {'YES' if has_tech else 'MISSING'}")
            print(f"    - Deliverables & Timeline: {'YES' if has_deliv else 'MISSING'}")
            print(f"    - Evaluation Criteria:     {'YES' if has_eval else 'MISSING'}")
            print(f"    - Submission Checklist:    {'YES' if has_check else 'MISSING'}")

            # Inspect documents
            cur.execute(
                """SELECT id, name, document_type, page_count, ocr_status, source,
                          (storage_path IS NOT NULL) AS stored
                   FROM documents WHERE case_id = %s ORDER BY id ASC""",
                (cid,),
            )
            docs = cur.fetchall()
            print(f"\n  Attached Documents ({len(docs)} total):")
            for d in docs:
                did, dname, dtype, dpages, docr, dsource, dstored = d
                stored_flag = "Stored" if dstored else "NO STORAGE"
                print(f"    [{did}] {dname} ({dtype or 'unknown'}) - Pages: {dpages or '?'} - OCR: {docr} - {stored_flag}")

            # Inspect recent jobs
            cur.execute(
                """SELECT id, job_type, status, error_message, created_at, updated_at
                   FROM jobs WHERE case_id = %s ORDER BY id DESC LIMIT 5""",
                (cid,),
            )
            jobs = cur.fetchall()
            print(f"\n  Recent Pipeline Jobs:")
            for j in jobs:
                jid, jtype, jstat, jerr, jcreated, jupdated = j
                err_str = f" - ERROR: {jerr}" if jerr else ""
                print(f"    Job {jid} ({jtype}): {jstat}{err_str}")

            print("=" * 60)
            if tri_stat != "complete" or not (has_sow and has_tech and has_check):
                print("RECOMMENDATION: To re-run triage now, execute:")
                print(f"  python backend/scripts/diagnose_triage.py --retry {sid}")
            else:
                print("STATUS: HEALTHY. All 3 critical triage artifacts are present and ready.")
            print("=" * 60)
    finally:
        conn.close()


def list_failed_solicitations():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, case_id, title, notice_id, ingestion_status, triage_status, triage_error
                   FROM solicitations
                   WHERE triage_status IN ('failed', 'running')
                      OR ingestion_status IN ('failed')
                   ORDER BY id DESC LIMIT 20"""
            )
            rows = cur.fetchall()
            if not rows:
                print("[✓] No failed or stalled solicitations found.")
                return
            print("=" * 70)
            print(f"FAILED / STALLED SOLICITATIONS ({len(rows)} found):")
            print("=" * 70)
            for r in rows:
                sid, cid, title, nid, ing_stat, tri_stat, tri_err = r
                print(f"Sol {sid} (Case {cid}) | Ingestion: {ing_stat} | Triage: {tri_stat}")
                print(f"  Title: {title}")
                if tri_err:
                    print(f"  Error: {tri_err}")
                print("-" * 70)
    finally:
        conn.close()


def retry_triage(solicitation_id: int):
    mgr = SolicitationManager()
    sol = mgr.get(solicitation_id)
    if not sol:
        print(f"[!] Solicitation {solicitation_id} not found.")
        return

    case_id = sol["case_id"]
    mgr.update(solicitation_id, triage_status="pending", triage_error=None)

    job = enqueue(
        case_id=case_id,
        job_type="solicitation_triage",
        metadata={"solicitation_id": solicitation_id},
    )
    print(f"[✓] Successfully enqueued triage job {job['id']} for solicitation {solicitation_id} (Case {case_id}).")
    print("Background worker will process the documents with on-demand tools.")


def main():
    parser = argparse.ArgumentParser(description="Vision Triage Pipeline Diagnostic & Recovery Tool")
    parser.add_argument("--solicitation", type=int, help="Solicitation ID to inspect")
    parser.add_argument("--case", type=int, help="Case ID to inspect")
    parser.add_argument("--list-failed", action="store_true", help="List all failed or stalled solicitations")
    parser.add_argument("--retry", type=int, help="Retry triage for given solicitation ID")

    args = parser.parse_args()

    if args.list_failed:
        list_failed_solicitations()
    elif args.retry:
        retry_triage(args.retry)
    elif args.solicitation:
        inspect_solicitation(solicitation_id=args.solicitation)
    elif args.case:
        inspect_solicitation(case_id=args.case)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
