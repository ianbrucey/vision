#!/usr/bin/env python3
"""
Vision — Background Job Worker.

Polls the jobs table, claims queued ingest jobs with SKIP LOCKED,
downloads files from MinIO, processes them, and updates job status.

Usage:
    cd scripts/vision && python -m backend.ingestion.worker
    # Or with a custom worker ID:
    VISION_WORKER_ID=worker-2 python -m backend.ingestion.worker

Run multiple workers for concurrent processing:
    for i in 1 2 3; do
        VISION_WORKER_ID=worker-$i python -m backend.ingestion.worker &
    done
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

# Ensure backend/ is on path (worker runs from backend/ directory)
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.db import connect
from ingestion.jobs import claim_next, mark_complete, mark_failed, update_progress, enqueue
from ingestion.storage import download_file, upload_file as _upload_to_minio
from ingestion.dispatcher import ingest_file
from ingestion.enricher import enrich_document
from ingestion.synthesizer import synthesize_case
from ingestion.profile_synth import synthesize_profile, generate_capability_statement

WORKER_ID = os.environ.get("VISION_WORKER_ID", f"worker-{os.getpid()}")
POLL_INTERVAL = 2  # seconds between polls when idle
TEMP_DIR = Path(os.environ.get("VISION_TEMP_DIR", "/tmp/vision-jobs"))


def process_ingest_job(job: dict) -> None:
    """Process a single ingest job: download → process → cleanup."""
    job_id = job["id"]
    case_id = job["case_id"]
    storage_ref = job.get("storage_ref") or {}

    bucket = storage_ref.get("bucket")
    object_key = storage_ref.get("object_key")
    original_name = storage_ref.get("original_name", "unknown")

    if not bucket or not object_key:
        mark_failed(job_id, "Missing storage reference")
        return

    # Download from MinIO
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    local_path = TEMP_DIR / f"{job_id}_{original_name}"

    try:
        print(f"[{WORKER_ID}] Job {job_id}: downloading {original_name}...")
        update_progress(job_id, 10)
        download_file(bucket, object_key, local_path)

        # Detect ZIP — extract and enqueue individual ingest jobs
        if original_name.lower().endswith(".zip"):
            _extract_zip_and_enqueue(job_id, case_id, local_path, original_name)
            return

        # Process based on file type
        print(f"[{WORKER_ID}] Job {job_id}: processing {original_name}...")
        update_progress(job_id, 30)

        from ingestion.dispatcher import ingest_file

        result = ingest_file(
            case_id=case_id,
            file_path=local_path,
            document_name=original_name,
        )
        update_progress(job_id, 90)

        doc_id = result.get("document_id")
        mark_complete(job_id, document_id=doc_id)

        # Enqueue enrichment — classify the document post-ingest
        try:
            enqueue(
                case_id=case_id,
                job_type="enrich",
                metadata={"document_id": doc_id},
            )
            print(f"[{WORKER_ID}] Job {job_id}: enqueued enrich for doc_id={doc_id}")
        except Exception as e:
            print(f"[{WORKER_ID}] Job {job_id}: failed to enqueue enrich — {e}")

        # Store the MinIO path on the document for preview/download
        storage_path = f"{bucket}/{object_key}"
        try:
            from core.db import tx
            with tx() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE documents SET storage_path = %s WHERE id = %s",
                        (storage_path, doc_id),
                    )
        except Exception:
            pass  # non-fatal — document was ingested successfully

        print(
            f"[{WORKER_ID}] Job {job_id}: complete — "
            f"doc_id={doc_id}, "
            f"{result.get('block_count', 0)} blocks"
        )

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))

    finally:
        # Clean up local temp file
        try:
            if local_path.exists():
                local_path.unlink()
        except OSError:
            pass


def process_enrich_job(job: dict) -> None:
    """Classify a newly ingested document via Agent SDK sub-agent."""
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    document_id = meta.get("document_id")

    if not document_id:
        mark_failed(job_id, "Missing document_id in job metadata")
        return

    try:
        print(f"[{WORKER_ID}] Job {job_id}: enriching doc_id={document_id}...")
        update_progress(job_id, 10)

        result = enrich_document(document_id=document_id, case_id=case_id)

        if result and "error" not in result:
            print(
                f"[{WORKER_ID}] Job {job_id}: enriched — "
                f"type={result.get('document_type')}, "
                f"tags={result.get('tags')}"
            )
        else:
            print(
                f"[{WORKER_ID}] Job {job_id}: enrichment returned — {result}"
            )

        update_progress(job_id, 100)
        mark_complete(job_id, document_id=document_id)

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: enrichment FAILED — {e}")
        traceback.print_exc()
        # Non-fatal — document is already ingested. Mark complete anyway
        # so the job doesn't retry forever. The document just won't have tags.
        mark_failed(job_id, str(e))


def _should_skip_zip_entry(entry_name: str) -> bool:
    """Filter out macOS resource forks, metadata dirs, and hidden junk files."""
    parts = entry_name.replace("\\", "/").split("/")
    for part in parts:
        # macOS resource fork files
        if part.startswith("._"):
            return True
        # macOS metadata directory
        if part == "__MACOSX":
            return True
    # Hidden files
    basename = parts[-1]
    if basename in (".DS_Store", "Thumbs.db", ".gitkeep"):
        return True
    if basename.startswith("~$"):  # Office temp files
        return True
    return False


def _extract_zip_and_enqueue(
    job_id: int, case_id: int, zip_path: Path, zip_name: str
) -> None:
    """Extract a ZIP archive and enqueue individual ingest jobs for its contents.

    Walks the full directory tree within the ZIP (including nested folders).
    Filters out macOS metadata (__MACOSX/, ._* resource forks, .DS_Store).
    Handles nested ZIPs recursively — zip inside zip inside zip, etc.
    """
    import zipfile, json, shutil

    extract_dir = TEMP_DIR / f"{job_id}_extracted"
    SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".jpg", ".jpeg", ".png", ".m4a", ".mp3", ".wav", ".zip"}
    MAX_DEPTH = 5  # zip-bomb guard — stop recursing after this many nested layers

    try:
        print(f"[{WORKER_ID}] Job {job_id}: extracting ZIP {zip_name}...")
        update_progress(job_id, 15)
        extract_dir.mkdir(parents=True, exist_ok=True)

        extracted_files: list[Path] = []
        skipped = 0
        depth = 0

        # Process zips recursively — queue starts with the outer zip,
        # any .zip entries found inside go back onto the queue.
        zip_queue: list[tuple[Path, Path]] = [(zip_path, extract_dir)]

        while zip_queue:
            depth += 1
            if depth > MAX_DEPTH:
                remaining = len(zip_queue)
                print(f"  [{WORKER_ID}]   ⚠ Max depth {MAX_DEPTH} reached — "
                      f"skipping {remaining} remaining nested zip(s)")
                break

            current_zip, dest_dir = zip_queue.pop(0)
            depth_tag = "" if depth == 1 else f"[depth {depth}] "

            try:
                with zipfile.ZipFile(current_zip, "r") as zf:
                    for entry in zf.infolist():
                        if entry.is_dir():
                            continue

                        if _should_skip_zip_entry(entry.filename):
                            skipped += 1
                            continue

                        member_path = dest_dir / entry.filename
                        member_path.parent.mkdir(parents=True, exist_ok=True)
                        zf.extract(entry, dest_dir)

                        suffix = member_path.suffix.lower()
                        if suffix not in SUPPORTED:
                            continue

                        if suffix == ".zip":
                            nested_dir = dest_dir / f"__nested__{member_path.stem}"
                            nested_dir.mkdir(parents=True, exist_ok=True)
                            zip_queue.append((member_path, nested_dir))
                        else:
                            extracted_files.append(member_path)
                            print(f"  [{WORKER_ID}]   → {depth_tag}{entry.filename}")
            except zipfile.BadZipFile:
                print(f"  [{WORKER_ID}]   ⚠ Skipping corrupt ZIP: {current_zip.name}")

        total = len(extracted_files)
        print(f"[{WORKER_ID}] Job {job_id}: {total} files extracted from ZIP")

        if total == 0:
            mark_complete(job_id)
            print(f"[{WORKER_ID}] Job {job_id}: no supported files found in ZIP")
            return

        update_progress(job_id, 30)

        # Upload each file to MinIO and enqueue individual ingest jobs
        child_job_ids = []
        for i, fpath in enumerate(extracted_files):
            pct = 30 + int((i / total) * 60)
            update_progress(job_id, pct)
            rel = fpath.relative_to(extract_dir)
            display_name = str(rel)

            try:
                print(f"  [{WORKER_ID}]   [{i+1}/{total}] uploading {display_name}...")
                f_storage_ref = _upload_to_minio(str(fpath), display_name)
                child_job = enqueue(
                    case_id=case_id,
                    job_type="ingest",
                    storage_ref=f_storage_ref,
                    metadata={"zip_source_job_id": job_id},
                )
                child_job_ids.append(child_job["id"])
            except Exception as e:
                print(f"  [{WORKER_ID}]   ⚠ Failed to enqueue {display_name}: {e}")

        # Mark the ZIP job complete with child references
        update_progress(job_id, 95)
        mark_complete(job_id)
        try:
            from core.db import tx
            with tx() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE jobs SET metadata = metadata || %s::jsonb WHERE id = %s",
                        (json.dumps({"child_job_ids": child_job_ids, "total_files": total}), job_id),
                    )
        except Exception:
            pass

        print(
            f"[{WORKER_ID}] Job {job_id}: ZIP extraction complete — "
            f"{len(child_job_ids)}/{total} files enqueued"
        )

    except zipfile.BadZipFile:
        print(f"[{WORKER_ID}] Job {job_id}: corrupted ZIP file")
        mark_failed(job_id, "Corrupted or password-protected ZIP file")
    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: ZIP extraction FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))
    finally:
        try:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
        except OSError:
            pass


def process_synthesize_job(job: dict) -> None:
    """Extract parties and allegations from the case narrative."""
    job_id = job["id"]
    case_id = job["case_id"]

    try:
        print(f"[{WORKER_ID}] Job {job_id}: synthesizing case {case_id}...")
        update_progress(job_id, 10)

        result = synthesize_case(case_id=case_id)

        print(
            f"[{WORKER_ID}] Job {job_id}: synthesized — "
            f"parties={result.get('parties_extracted', 0)}, "
            f"allegations={result.get('allegations_extracted', 0)}"
        )

        update_progress(job_id, 100)
        mark_complete(job_id)

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: synthesis FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))


def process_capability_statement_job(job: dict) -> None:
    """Generate a capability statement draft from profile data."""
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    profile_id = meta.get("profile_id")

    if not profile_id:
        mark_failed(job_id, "Missing profile_id")
        return

    try:
        print(f"[{WORKER_ID}] Job {job_id}: generating capability statement for profile {profile_id}...")
        update_progress(job_id, 10)
        result = generate_capability_statement(profile_id=profile_id, case_id=case_id)
        print(f"[{WORKER_ID}] Job {job_id}: capability statement — {result}")
        update_progress(job_id, 100)
        mark_complete(job_id)
    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: capability statement FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))


def process_profile_synthesis_job(job: dict) -> None:
    """Run company profile synthesis."""
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    profile_id = meta.get("profile_id")

    if not profile_id:
        mark_failed(job_id, "Missing profile_id in job metadata")
        return

    try:
        print(f"[{WORKER_ID}] Job {job_id}: synthesizing profile {profile_id}...")
        update_progress(job_id, 10)

        result = synthesize_profile(profile_id=profile_id, case_id=case_id)

        print(
            f"[{WORKER_ID}] Job {job_id}: profile synthesized — "
            f"fields={result.get('fields_populated', 0)}"
        )
        update_progress(job_id, 100)
        mark_complete(job_id)

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: profile synthesis FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))


def main():
    """Main loop — poll for jobs, process, repeat."""
    print(f"[{WORKER_ID}] Worker started. Polling every {POLL_INTERVAL}s...")
    print(f"[{WORKER_ID}] Temp files: {TEMP_DIR}")

    while True:
        try:
            job = claim_next(WORKER_ID)
            if job is None:
                time.sleep(POLL_INTERVAL)
                continue

            print(f"[{WORKER_ID}] Claimed job {job['id']}: {job['job_type']}")

            if job["job_type"] == "ingest":
                process_ingest_job(job)
            elif job["job_type"] == "enrich":
                process_enrich_job(job)
            elif job["job_type"] == "synthesize":
                process_synthesize_job(job)
            elif job["job_type"] == "profile_synthesis":
                process_profile_synthesis_job(job)
            elif job["job_type"] == "capability_statement":
                process_capability_statement_job(job)
            else:
                mark_failed(job["id"], f"Unknown job type: {job['job_type']}")

        except KeyboardInterrupt:
            print(f"\n[{WORKER_ID}] Shutting down.")
            break
        except Exception as e:
            print(f"[{WORKER_ID}] Worker error: {e}")
            traceback.print_exc()
            time.sleep(5)  # back off on unexpected errors


if __name__ == "__main__":
    main()
