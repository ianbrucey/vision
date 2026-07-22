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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Ensure backend/ is on path (worker runs from backend/ directory)
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.db import connect
from core.case import CaseManager
from core.solicitation import SolicitationManager
from ingestion.jobs import claim_next, mark_complete, mark_failed, update_progress, enqueue
from ingestion.storage import download_file, upload_file as _upload_to_minio
from ingestion.dispatcher import ingest_file
from ingestion.enricher import enrich_document
from ingestion.synthesizer import synthesize_case
from ingestion.profile_synth import synthesize_profile, generate_capability_statement
from ingestion.sam_client import (
    fetch_notice, fetch_description, download_resource_link, SamFetchError,
)
from ingestion.solicitation_triage import run_solicitation_triage_pipeline
from ingestion.vendor_matching import run_vendor_matching_pipeline_sync

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


def _build_solicitation_narrative(metadata: dict[str, Any], description: str) -> str:
    """Compose a short grounding narrative for `cases.narrative` from
    SAM.gov metadata + description text (see T5 in
    context-engine/specs/ux-refinements/TICKETS.md).

    Returns "" if there isn't enough data to make a meaningful sentence
    (e.g. sparse notices — see 03-fixtures.json Example 2, which has null
    naicsCode/pointOfContact/placeOfPerformance).
    """
    parts: list[str] = []

    agency = metadata.get("agency")
    title = metadata.get("title")
    if agency and title:
        parts.append(f"{agency} is soliciting: {title}.")
    elif agency:
        parts.append(f"Posted by {agency}.")
    elif title:
        parts.append(f"{title}.")

    details = []
    naics = metadata.get("naics_code")
    if naics:
        details.append(f"NAICS {naics}")
    set_aside = metadata.get("set_aside_description") or metadata.get("set_aside_type")
    if set_aside:
        details.append(f"set-aside: {set_aside}")
    deadline = metadata.get("response_deadline")
    if deadline:
        details.append(f"response deadline {deadline}")
    if details:
        joined = ", ".join(details) + "."
        parts.append(joined[:1].upper() + joined[1:])

    if description:
        parts.append(description[:1000])

    return " ".join(parts).strip()


def process_sam_fetch_job(job: dict) -> None:
    """Fetch SAM.gov opportunity metadata + attachments for a federal solicitation.

    job['metadata'] must contain {"solicitation_id": int, "notice_id": str}
    (set by the /api/solicitations POST route at enqueue time).
    """
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    solicitation_id = meta.get("solicitation_id")
    notice_id = meta.get("notice_id")

    if not solicitation_id or not notice_id:
        mark_failed(job_id, "Missing solicitation_id/notice_id in job metadata")
        return

    mgr = SolicitationManager()
    mgr.update(solicitation_id, ingestion_status="fetching")

    try:
        print(f"[{WORKER_ID}] Job {job_id}: fetching SAM.gov notice {notice_id}...")
        update_progress(job_id, 10)
        notice = fetch_notice(notice_id)
    except SamFetchError as e:
        print(f"[{WORKER_ID}] Job {job_id}: SAM fetch FAILED — {e}")
        mgr.update(solicitation_id, ingestion_status="failed", error_message=str(e))
        mark_failed(job_id, str(e))
        return

    metadata_updates: dict[str, Any] = {
        "agency": notice.get("fullParentPathName"),
        "naics_code": notice.get("naicsCode"),
        "psc_code": notice.get("classificationCode"),
        "set_aside_type": notice.get("typeOfSetAside"),
        "set_aside_description": notice.get("typeOfSetAsideDescription"),
        "point_of_contact": notice.get("pointOfContact"),
        "place_of_performance": notice.get("placeOfPerformance"),
        "response_deadline": notice.get("responseDeadLine"),
        "posted_date": notice.get("postedDate"),
    }
    # title is NOT NULL — only overwrite the placeholder if SAM.gov gave us
    # a real one; never blank it out.
    if notice.get("title"):
        metadata_updates["title"] = notice["title"]

    mgr.update(solicitation_id, **metadata_updates)
    update_progress(job_id, 30)

    # Ground the agent immediately: synthesize a narrative from what SAM.gov
    # gave us and write it to cases.narrative, but only if the user hasn't
    # already written their own (narrative is still blank/NULL).
    try:
        description = fetch_description(notice_id)
        narrative = _build_solicitation_narrative(metadata_updates, description)
        if narrative:
            case_mgr = CaseManager()
            current_case = case_mgr.get_case(case_id)
            if current_case is not None and not (current_case.get("narrative") or "").strip():
                case_mgr.update_case(case_id, narrative=narrative)
    except Exception as e:
        # Non-fatal — narrative is a nice-to-have, never block sam_fetch on it.
        print(f"[{WORKER_ID}] Job {job_id}: narrative synthesis failed (non-fatal) — {e}")

    resource_links = notice.get("resourceLinks") or []
    has_missing_docs = False

    if not resource_links:
        has_missing_docs = True
    else:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        total = len(resource_links)

        # ── Phase 1: download all attachments in parallel ──────────
        # Each resource link is a SAM.gov S3-presigned URL — purely I/O bound.
        # Threading cuts wall-clock time from Σ(downloads) to max(downloads).
        downloads: list[dict | Exception] = [None] * total  # type: ignore[list-item]

        def _download_one(idx: int, link: str) -> tuple[int, dict | Exception]:
            local_path = TEMP_DIR / f"{job_id}_sam_{idx}"
            try:
                return (idx, download_resource_link(link, local_path))
            except Exception as e:
                return (idx, e)

        with ThreadPoolExecutor(max_workers=min(total, 6)) as pool:
            futures = [
                pool.submit(_download_one, i, link)
                for i, link in enumerate(resource_links)
            ]
            for future in as_completed(futures):
                idx, result = future.result()
                downloads[idx] = result

        update_progress(job_id, 60)

        # ── Phase 2: ingest all downloads in parallel ─────────────
        # Each document is independent — download, OCR, MinIO upload,
        # and DB writes don't contend on shared rows. ThreadPoolExecutor
        # overlaps I/O (MinIO uploads) with CPU (OCR).
        def _process_one(idx: int, result: dict | Exception) -> bool:
            """Process a single downloaded file. Returns True on success."""
            if isinstance(result, Exception):
                print(
                    f"[{WORKER_ID}] Job {job_id}: resource {idx+1}/{total} "
                    f"download FAILED — {result}"
                )
                return False

            filename = result["filename"]
            fpath = result["path"]

            # Rename to carry the correct suffix before dispatching.
            suffix = Path(filename).suffix
            if suffix and fpath.suffix != suffix:
                renamed = fpath.with_suffix(suffix)
                fpath.rename(renamed)
                fpath = renamed

            try:
                print(
                    f"[{WORKER_ID}] Job {job_id}: ingesting resource "
                    f"{idx+1}/{total} — {filename}"
                )
                ingest_result = ingest_file(
                    case_id=case_id,
                    file_path=fpath,
                    document_name=filename,
                )
                doc_id = ingest_result.get("document_id")

                # Upload to MinIO for durable storage/preview.
                storage_ref = _upload_to_minio(fpath, filename)
                storage_path = f"{storage_ref['bucket']}/{storage_ref['object_key']}"

                if doc_id:
                    from core.db import tx
                    with tx() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE documents SET source = 'sam_gov', "
                                "storage_path = %s WHERE id = %s",
                                (storage_path, doc_id),
                            )
                    try:
                        enqueue(
                            case_id=case_id,
                            job_type="enrich",
                            metadata={"document_id": doc_id},
                        )
                    except Exception as e:
                        print(
                            f"[{WORKER_ID}] Job {job_id}: failed to enqueue "
                            f"enrich — {e}"
                        )

                print(
                    f"[{WORKER_ID}] Job {job_id}: ingested {filename} "
                    f"(doc_id={doc_id})"
                )
                return True
            except Exception as e:
                print(
                    f"[{WORKER_ID}] Job {job_id}: resource {idx+1}/{total} "
                    f"ingest FAILED — {e}"
                )
                traceback.print_exc()
                return False
            finally:
                try:
                    if fpath.exists():
                        fpath.unlink()
                except OSError:
                    pass

        with ThreadPoolExecutor(max_workers=min(total, 6)) as pool:
            results = list(pool.map(
                _process_one,
                range(total),
                downloads,
            ))

        update_progress(job_id, 95)
        if any(not ok for ok in results):
            has_missing_docs = True

    update_progress(job_id, 100)
    mgr.update(solicitation_id, ingestion_status="complete", has_missing_docs=has_missing_docs)
    mark_complete(job_id)
    print(
        f"[{WORKER_ID}] Job {job_id}: sam_fetch complete — "
        f"has_missing_docs={has_missing_docs}"
    )

    # Auto-trigger the unattended triage pipeline — only when document
    # retrieval fully succeeded. If any docs are missing, leave it for the
    # manual "Run Triage" trigger instead (per product decision).
    if not has_missing_docs:
        try:
            enqueue(
                case_id=case_id,
                job_type="solicitation_triage",
                metadata={"solicitation_id": solicitation_id},
            )
            print(
                f"[{WORKER_ID}] Job {job_id}: enqueued solicitation_triage "
                f"for solicitation_id={solicitation_id}"
            )
        except Exception as e:
            print(f"[{WORKER_ID}] Job {job_id}: failed to enqueue solicitation_triage — {e}")


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


def process_solicitation_triage_job(job: dict) -> None:
    """Run the unattended solicitation triage pipeline for a solicitation.

    Fully unattended — no human checkpoints. Classifies notice type, runs
    quick-kill, and (if it passes) extracts the 5 partner-facing HTML
    artifacts concurrently. See ingestion/solicitation_triage.py.
    """
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    solicitation_id = meta.get("solicitation_id")

    if not solicitation_id:
        mark_failed(job_id, "Missing solicitation_id in job metadata")
        return

    try:
        print(f"[{WORKER_ID}] Job {job_id}: running triage for solicitation_id={solicitation_id}...")
        update_progress(job_id, 10)

        result = run_solicitation_triage_pipeline(case_id=case_id, solicitation_id=solicitation_id)

        if result.get("error"):
            print(f"[{WORKER_ID}] Job {job_id}: triage FAILED — {result['error']}")
            mark_failed(job_id, result["error"])
            return

        if result.get("quick_kill"):
            print(
                f"[{WORKER_ID}] Job {job_id}: triage complete — QUICK-KILL "
                f"({result.get('notice_type')}): {result.get('reason')}"
            )
        else:
            print(
                f"[{WORKER_ID}] Job {job_id}: triage complete — "
                f"notice_type={result.get('notice_type')}, "
                f"has_partial_artifacts={result.get('has_partial_artifacts')}"
            )

        update_progress(job_id, 100)
        mark_complete(job_id)

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: triage FAILED — {e}")
        traceback.print_exc()
        try:
            SolicitationManager().update(solicitation_id, triage_status="failed", triage_error=str(e))
        except Exception:
            pass
        mark_failed(job_id, str(e))


def process_vendor_matching_job(job: dict) -> None:
    """Run the unattended vendor-matching pipeline for a solicitation.

    Fully unattended — no human checkpoints. Builds a deterministic SQL
    candidate pool, then runs a single ranking/outreach-drafting agent.
    See ingestion/vendor_matching.py.
    """
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    solicitation_id = meta.get("solicitation_id")

    if not solicitation_id:
        mark_failed(job_id, "Missing solicitation_id in job metadata")
        return

    try:
        print(f"[{WORKER_ID}] Job {job_id}: running vendor matching for solicitation_id={solicitation_id}...")
        update_progress(job_id, 10)

        result = run_vendor_matching_pipeline_sync(case_id=case_id, solicitation_id=solicitation_id)

        if result.get("error"):
            print(f"[{WORKER_ID}] Job {job_id}: vendor matching FAILED — {result['error']}")
            mark_failed(job_id, result["error"])
            return

        print(
            f"[{WORKER_ID}] Job {job_id}: vendor matching complete — "
            f"match_count={result.get('match_count')}"
        )

        update_progress(job_id, 100)
        mark_complete(job_id)

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: vendor matching FAILED — {e}")
        traceback.print_exc()
        try:
            SolicitationManager().update(solicitation_id, matching_status="failed", matching_error=str(e))
        except Exception:
            pass
        mark_failed(job_id, str(e))


def process_inbound_email_job(job: dict) -> None:
    """Store an inbound Mailgun reply as a document + flip outreach_status.

    job['metadata'] = {"vendor_match_id": int, "sender": str,
                        "subject": str, "text": str} — set by
    api/routes/webhooks_mailgun.py at enqueue time.

    Creates a documents row with source='email' (an existing, already-
    allowed value in the documents.source CHECK constraint — see
    001_core.sql line 167-170) containing the reply's sender/subject/body
    as plain text (no attachment/MinIO upload — T10b v1 stores the body
    text only; a follow-up ticket can add multipart attachment handling
    if replies carry file attachments). Links the new document to the
    vendor_matches row via outreach_doc_id and sets outreach_status='received'
    by calling core/vendor_match.py's existing update_outreach() — the
    same code path a manual status change uses (per 013_vendor_outreach.sql's
    original design intent).
    """
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    vendor_match_id = meta.get("vendor_match_id")
    sender = meta.get("sender", "unknown")
    subject = meta.get("subject", "(no subject)")
    text = meta.get("text", "")

    if not vendor_match_id:
        mark_failed(job_id, "Missing vendor_match_id in job metadata")
        return

    try:
        from core.db import tx, insert_document
        from core.vendor_match import VendorMatchManager

        doc_name = f"Reply from {sender} — {subject}"[:250]
        content = f"From: {sender}\nSubject: {subject}\n\n{text}"

        with tx() as conn:
            doc_id = insert_document(
                conn,
                case_id=case_id,
                name=doc_name,
                source="email",
                metadata={"vendor_match_id": vendor_match_id, "sender": sender},
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET storage_path = NULL WHERE id = %s",
                    (doc_id,),
                )

        # Store the body text so it's readable — documents needs at least
        # one section/block to render in DocumentPreviewModal.
        from core.db import insert_section, insert_block
        with tx() as conn:
            section_id = insert_section(conn, document_id=doc_id, title=subject, search_text=content)
            insert_block(conn, document_id=doc_id, section_id=section_id, text_content=content)

        mgr = VendorMatchManager()
        mgr.update_outreach(
            vendor_match_id, outreach_status="received", outreach_doc_id=doc_id
        )
        mgr.record_inbound_message(
            vendor_match_id, subject=subject, body=content, document_id=doc_id
        )

        mark_complete(job_id, document_id=doc_id)
        print(f"[{WORKER_ID}] Job {job_id}: inbound email stored as doc_id={doc_id}, vendor_match_id={vendor_match_id}")

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: inbound email processing FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))


def process_sam_notice_import_job(job: dict) -> None:
    """Import a SAM.gov databank CSV into the sam_notices table.

    job['metadata'] = {"file_path": str, "original_name": str, "batch_id": str}
    set by api/routes/sam_notices.py at upload time.
    """
    import csv as _csv
    import uuid
    from datetime import datetime as _dt
    from pathlib import Path as _Path

    job_id = job["id"]
    meta = job.get("metadata") or {}
    file_path = meta.get("file_path")
    original_name = meta.get("original_name", "unknown.csv")
    batch_id = meta.get("batch_id", str(uuid.uuid4()))

    if not file_path:
        mark_failed(job_id, "Missing file_path in job metadata")
        return

    csv_path = _Path(file_path)
    if not csv_path.exists():
        mark_failed(job_id, f"CSV file not found: {file_path}")
        return

    _DATE_COLS = {"current_response_date", "last_published_date",
                  "inactive_date", "last_updated_date"}

    _COL_MAP = {
        "Notice ID": "notice_id", "Opportunity Title": "opportunity_title",
        "Contract Opportunity Type": "contract_opportunity_type",
        "Description": "description", "Status": "status",
        "Current Response Date": "current_response_date",
        "Last Published Date": "last_published_date",
        "Inactive Date": "inactive_date", "Last Updated Date": "last_updated_date",
        "NAICS": "naics_code", "PSC": "psc_code",
        "Current Set Aside": "current_set_aside",
        "Current Set Aside Code": "current_set_aside_code", "Initiative": "initiative",
        "Contracting Office": "contracting_office",
        "Procurement AAC Code": "procurement_aac_code",
        "Sub Tier Code": "sub_tier_code", "Sub Tier Name": "sub_tier_name",
        "Place of Performance - Country": "pop_country",
        "Place of Performance - Zip": "pop_zip",
        "Place of Performance - City": "pop_city",
        "Place of Performance - State": "pop_state",
        "POC Name": "poc_name", "POC Email": "poc_email",
        "Unique Entity ID": "awardee_uei", "Legal Business Name": "awardee_name",
        "Package Attachment Count (Public)": "attachment_count",
        "Interested Vendor List (IVL) Enabled": "ivl_enabled",
    }

    try:
        db_cols = list(_COL_MAP.values()) + ["upload_batch_id", "source_csv"]
        placeholders = ", ".join(["%s"] * len(db_cols))
        col_list = ", ".join(db_cols)
        sql = f"INSERT INTO sam_notices ({col_list}) VALUES ({placeholders})"

        rows_inserted = 0
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = _csv.DictReader(f)
            batch = []
            with tx() as conn:
                with conn.cursor() as cur:
                    for row in reader:
                        vals = []
                        for db_col in db_cols:
                            if db_col in ("upload_batch_id", "source_csv"):
                                continue
                            csv_col = db_col  # same name in our mapped dict
                            val = (row.get(csv_col) or "").strip()
                            if not val:
                                vals.append(None)
                            elif db_col in _DATE_COLS:
                                parsed = None
                                for fmt in ["%b %d, %Y %I:%M %p UTC", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                                    try:
                                        parsed = _dt.strptime(val, fmt)
                                        break
                                    except ValueError:
                                        continue
                                vals.append(parsed)
                            elif db_col == "attachment_count":
                                try: vals.append(int(val))
                                except: vals.append(None)
                            elif db_col == "ivl_enabled":
                                vals.append(val.lower() in ("true", "yes", "1", "t"))
                            else:
                                vals.append(val)
                        vals.append(batch_id)
                        vals.append(original_name)
                        batch.append(vals)

                        if len(batch) >= 500:
                            for b in batch:
                                cur.execute(sql, b)
                            rows_inserted += len(batch)
                            batch = []

                    for b in batch:
                        cur.execute(sql, b)
                    rows_inserted += len(batch)

        # Clean up temp file
        try:
            csv_path.unlink()
        except Exception:
            pass

        mark_complete(job_id)
        print(f"[{WORKER_ID}] Job {job_id}: imported {rows_inserted} SAM notices from {original_name}")

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: SAM notice import FAILED — {e}")
        traceback.print_exc()
        try:
            csv_path.unlink()
        except Exception:
            pass
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
            elif job["job_type"] == "sam_fetch":
                process_sam_fetch_job(job)
            elif job["job_type"] == "solicitation_triage":
                process_solicitation_triage_job(job)
            elif job["job_type"] == "vendor_matching":
                process_vendor_matching_job(job)
            elif job["job_type"] == "inbound_email":
                process_inbound_email_job(job)
            elif job["job_type"] == "sam_notice_import":
                process_sam_notice_import_job(job)
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
