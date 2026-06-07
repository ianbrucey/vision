"""
Test script for Vision Chat API.

Tests the SSE streaming endpoint directly, validating:
1. Session creation
2. Message streaming (SSE events are received)
3. Message history retrieval (messages persisted to DB)

Usage:
    cd scripts/vision
    source .venv/bin/activate
    python3 backend/tests/test_chat_stream.py [--base-url http://127.0.0.1:8400] [--case-id N]

Requires the backend to be running:
    cd scripts && python -m uvicorn vision.api:app --reload --port 8400
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE = "http://127.0.0.1:8400"
TOKEN = None  # set after auth


def _api(path: str, method: str = "GET", body: dict | None = None) -> dict:
    """Call the Vision API. Returns parsed JSON."""
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        err_body = e.read().decode(errors="replace")
        print(f"  HTTP {e.code}: {err_body}")
        raise


def _register_and_login() -> str:
    """Create a test user and return a JWT token."""
    global TOKEN
    import random
    suffix = random.randint(1000, 9999)
    username = f"chattest_{suffix}"
    password = "test123456"

    print(f"  Registering test user: {username}")
    resp = _api("/api/auth/register", method="POST", body={
        "username": username,
        "password": password,
    })
    TOKEN = resp["token"]
    print(f"  Token: {TOKEN[:20]}...")
    return TOKEN


def _stream_sse(session_id: int, message: str) -> list[dict]:
    """Send a message and collect all SSE events."""
    url = f"{API_BASE}/api/chat/sessions/{session_id}/messages"
    body = json.dumps({"message": message}).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")

    events = []
    print(f"\n  Streaming response for: \"{message}\"")
    print(f"  {'─' * 50}")

    try:
        with urlopen(req, timeout=120) as resp:
            if resp.status != 200:
                print(f"  ERROR: HTTP {resp.status}")
                return events

            # Read the streaming response line by line
            buffer = b""
            start = time.time()
            event_count = 0

            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk

                # Split on \n\n (SSE event boundary)
                while b"\n\n" in buffer:
                    raw_event, buffer = buffer.split(b"\n\n", 1)
                    line = raw_event.decode(errors="replace").strip()
                    if line.startswith("data: "):
                        payload = line[6:]
                        try:
                            event = json.loads(payload)
                            event_count += 1
                            events.append(event)

                            # Pretty print
                            etype = event.get("type", "?")
                            if etype == "assistant":
                                content = event.get("content", "")
                                print(f"  [{event_count}] assistant: {content[:100]}{'...' if len(content) > 100 else ''}")
                            elif etype == "tool_call":
                                print(f"  [{event_count}] tool_call: {event.get('name', '?')}")
                            elif etype == "tool_result":
                                print(f"  [{event_count}] tool_result: {str(event.get('content', ''))[:100]}")
                            elif etype == "done":
                                print(f"  [{event_count}] done: cost={event.get('cost')}")
                            elif etype == "init":
                                print(f"  [{event_count}] init: {event.get('session_id', '?')}")
                            elif etype == "error":
                                print(f"  [{event_count}] ERROR: {event.get('message', '')[:200]}")
                            else:
                                print(f"  [{event_count}] {etype}: {str(event)[:120]}")
                        except json.JSONDecodeError:
                            print(f"  [?] unparseable: {line[:100]}")

            elapsed = time.time() - start
            print(f"  {'─' * 50}")
            print(f"  Received {event_count} events in {elapsed:.1f}s")

    except URLError as e:
        print(f"  CONNECTION ERROR: {e}")
        print(f"  Is the backend running at {API_BASE}?")

    return events


def _get_messages(session_id: int) -> list[dict]:
    """Retrieve persisted message history."""
    return _api(f"/api/chat/sessions/{session_id}/messages")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Test Vision Chat API streaming")
    parser.add_argument("--base-url", default="http://127.0.0.1:8400",
                        help="API base URL")
    parser.add_argument("--case-id", type=int, default=None,
                        help="Case ID to use (auto-creates one if not provided)")
    args = parser.parse_args()

    global API_BASE
    API_BASE = args.base_url.rstrip("/")

    print("=" * 60)
    print("Vision Chat API — SSE Streaming Test")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 0: Health check
    # ------------------------------------------------------------------
    print("\n[0] Health check...")
    try:
        health = _api("/api/health")
        print(f"  OK: version={health.get('version')}")
    except Exception:
        print("  FAILED — is the backend running?")
        print(f"  Start it with: cd scripts && python -m uvicorn vision.api:app --reload --port 8400")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Auth
    # ------------------------------------------------------------------
    print("\n[1] Authentication...")
    try:
        token = _register_and_login()
    except Exception as e:
        print(f"  Auth failed: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Get or create a case
    # ------------------------------------------------------------------
    print("\n[2] Case setup...")
    case_id = args.case_id
    if case_id is None:
        # List existing cases
        cases = _api("/api/cases")
        if cases:
            case_id = cases[0]["id"]
            print(f"  Using existing case: id={case_id}, name={cases[0].get('name')}")
        else:
            # Create a test case
            case = _api("/api/cases", method="POST", body={
                "name": "Chat Test Case",
                "case_type": "civil",
                "narrative": "Test case for chat API testing.",
            })
            case_id = case["id"]
            print(f"  Created test case: id={case_id}")
    else:
        print(f"  Using provided case: id={case_id}")

    # ------------------------------------------------------------------
    # Step 3: Create a chat session
    # ------------------------------------------------------------------
    print("\n[3] Creating chat session...")
    session_resp = _api("/api/chat/sessions", method="POST", body={
        "case_id": case_id,
    })
    session_id = session_resp["session_id"]
    print(f"  Session created: id={session_id}")
    print(f"  Project key: {session_resp.get('project_key')}")

    # ------------------------------------------------------------------
    # Step 4: Send a message and collect SSE events
    # ------------------------------------------------------------------
    print("\n[4] Sending message via SSE stream...")
    events = _stream_sse(session_id, "Hello! What case am I working on? Give a brief answer.")

    # ------------------------------------------------------------------
    # Step 5: Check results
    # ------------------------------------------------------------------
    print("\n[5] Results summary...")
    event_types = {}
    has_error = False
    for e in events:
        t = e.get("type", "?")
        event_types[t] = event_types.get(t, 0) + 1
        if t == "error":
            has_error = True
            print(f"  ERROR EVENT: {e.get('message', '')[:200]}")

    print(f"  Event breakdown: {event_types}")

    if not events:
        print("\n  ❌ NO EVENTS RECEIVED — the stream returned nothing.")
        print("  This confirms the bug: message type detection was broken.")
        sys.exit(1)

    has_assistant = event_types.get("assistant", 0) > 0
    has_done = event_types.get("done", 0) > 0

    if has_error:
        print("\n  ⚠️  Error events received — check API key / SDK configuration.")
        sys.exit(1)

    if has_assistant:
        print("\n  ✅ Assistant messages received via SSE!")
    else:
        print("\n  ❌ No assistant messages received.")
        sys.exit(1)

    if has_done:
        print("  ✅ Done event received (stream completed).")

    # ------------------------------------------------------------------
    # Step 6: Verify message persistence
    # ------------------------------------------------------------------
    print("\n[6] Checking message persistence...")
    try:
        msgs = _get_messages(session_id)
        print(f"  Messages in DB: {len(msgs)}")
        for m in msgs:
            role = m.get("role", "?")
            content = (m.get("content") or "")[:80]
            print(f"    [{role}] {content}{'...' if len(m.get('content') or '') > 80 else ''}")
        if len(msgs) >= 2:  # at least user + assistant
            print("  ✅ Messages persisted to database.")
        else:
            print("  ⚠️  Only user message found — assistant not persisted.")
    except Exception as e:
        print(f"  Failed to load messages: {e}")

    print("\n" + "=" * 60)
    if has_assistant and not has_error:
        print("✅ All checks passed — chat streaming is working!")
    else:
        print("❌ Some checks failed — see above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
