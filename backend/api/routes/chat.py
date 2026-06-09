"""
Vision — Chat API Routes.

FastAPI routes for the conversational agent interface:
  - Session CRUD (create, list, get, archive)
  - Message history
  - SSE streaming for agent responses
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user
from chat.manager import ChatManager

logger = logging.getLogger("vision.chat.routes")

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Singleton — one manager per process
_manager: ChatManager | None = None


def _get_manager() -> ChatManager:
    global _manager
    if _manager is None:
        _manager = ChatManager()
    return _manager


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    case_id: int
    system_prompt: str | None = None


class SendMessageRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new chat session for a case."""
    mgr = _get_manager()
    session = await mgr.create_session(
        case_id=body.case_id,
        system_prompt=body.system_prompt,
    )
    return session


@router.get("/sessions")
async def list_sessions(
    case_id: int,
    user: dict = Depends(get_current_user),
):
    """List active chat sessions for a case."""
    mgr = _get_manager()
    return await mgr.list_sessions(case_id=case_id)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    """Get session metadata."""
    mgr = _get_manager()
    session = await mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def archive_session(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    """Archive a session."""
    mgr = _get_manager()
    ok = await mgr.archive_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"archived": True}


# ---------------------------------------------------------------------------
# Message endpoints
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    """Get message history for a session."""
    mgr = _get_manager()
    session = await mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await mgr.get_messages(session_id)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    body: SendMessageRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Send a message and stream the agent response via SSE."""
    mgr = _get_manager()
    session = await mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream() -> AsyncIterator[str]:
        """SSE event generator. Detects client disconnect."""
        try:
            async for sse_event in mgr.stream_message(session_id, body.message):
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                yield sse_event
        except Exception as exc:
            logger.exception("SSE stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ---------------------------------------------------------------------------
# Voice-to-text transcription
# ---------------------------------------------------------------------------

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Transcribe an audio file via Mistral speech-to-text.

    Accepts a short audio recording (webm, m4a, mp3, wav) and returns the
    transcribed text. For use with the mic button in the chat input.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = Path(file.filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        from mistralai.client import Mistral

        # Load API key (same pattern as dispatcher.py)
        mistral_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_key:
            for env_path in [
                Path(__file__).resolve().parents[3] / ".env",
                Path(__file__).resolve().parents[3] / "mcp-server" / ".env",
            ]:
                if env_path.exists():
                    for line in env_path.read_text().splitlines():
                        if line.startswith("MISTRAL_API_KEY="):
                            mistral_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        if not mistral_key:
            raise HTTPException(status_code=500, detail="MISTRAL_API_KEY not configured")

        client = Mistral(api_key=mistral_key)
        file_id = None

        try:
            # Upload audio file
            with open(tmp_path, "rb") as f:
                uploaded = client.files.upload(
                    file={"file_name": file.filename or "recording.webm", "content": f},
                    purpose="audio",
                )
            file_id = uploaded.id

            # Get signed URL
            signed = client.files.get_signed_url(file_id=file_id)

            # Transcribe
            transcription = client.audio.transcriptions.complete(
                model="voxtral-mini-latest",
                file_url=signed.url,
            )

            return {"text": transcription.text}

        finally:
            if file_id:
                try:
                    client.files.delete(file_id=file_id)
                except Exception:
                    pass

    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
