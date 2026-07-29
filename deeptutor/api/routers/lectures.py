"""Durable, non-blocking lecture and course-media library."""
from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import shutil
import subprocess
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

import requests

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from deeptutor.agents.notebook import NotebookSummarizeAgent
from deeptutor.services.path_service import get_path_service
from deeptutor.services.voice import transcribe_audio

router = APIRouter()
_MEDIA_TYPES = {"audio/webm", "audio/mpeg", "audio/mp4", "audio/wav", "video/mp4", "video/webm", "video/quicktime"}


class Echo360Source(BaseModel):
    """A selected, browser-resolved Echo360 source; it never contains cookies."""

    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    date: str = Field(default="", max_length=32)
    course_id: str = Field(min_length=1, max_length=128)
    course_name: str = Field(default="", max_length=500)
    media_url: str = Field(min_length=8, max_length=4096)
    media_kind: Literal["mp4", "hls"]


class Echo360ImportRequest(BaseModel):
    """Selected sources resolved inside the user's authenticated browser."""

    course_id: str = Field(min_length=1, max_length=128)
    sources: list[Echo360Source] = Field(min_length=1, max_length=25)
    kb_name: str = Field(default="", max_length=200)


def _root() -> Path:
    path = get_path_service().get_user_root() / "media_library"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read(item_dir: Path) -> dict:
    try:
        return json.loads((item_dir / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(404, "Library item not found.") from None


def _write(item_dir: Path, data: dict) -> None:
    (item_dir / "metadata.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _auto_title(transcript: str, fallback: str) -> str:
    first = re.split(r"[.!?\n]", transcript.strip(), maxsplit=1)[0].strip()
    return first[:90].rstrip() or Path(fallback).stem or "Untitled lecture"


async def _index_notes(kb_name: str, notes_path: Path) -> str | None:
    if not kb_name:
        return None
    from deeptutor.api.routers import knowledge
    manager, resolved, base_dir = knowledge._writable_kb(kb_name)
    entry = knowledge._load_kb_entry_or_404(manager, resolved)
    provider = knowledge._validate_registered_provider(entry.get("rag_provider") or knowledge.DEFAULT_PROVIDER)
    task_id = knowledge._build_unique_task_id("media_library", resolved)
    await knowledge.run_upload_processing_task(resolved, str(base_dir), [str(notes_path)], task_id, provider)
    return task_id


def _fmt_vtt_time(seconds: float) -> str:
    """Format float seconds to VTT timestamp ``HH:MM:SS.mmm``."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


async def _process(item_id: str) -> None:
    item_dir = _root() / item_id
    meta = _read(item_dir)
    media = item_dir / meta["media_file"]
    try:
        meta.update(status="transcribing", progress="Transcribing media…")
        _write(item_dir, meta)
        raw = await transcribe_audio(
            media.read_bytes(),
            filename=media.name,
            content_type=meta["content_type"],
            response_format="verbose_json",
        )
        data = json.loads(raw)
        transcript = data["text"]
        segments = data.get("segments") or []

        # Generate WebVTT subtitles.
        vtt_lines = ["WEBVTT\n"]
        for seg in segments:
            start = _fmt_vtt_time(seg["start"])
            end = _fmt_vtt_time(seg["end"])
            text = seg["text"].strip()
            vtt_lines.append(f"{start} --> {end}")
            vtt_lines.append(text + "\n")
        vtt_content = "\n".join(vtt_lines)

        title = _auto_title(transcript, meta["original_name"])
        meta.update(status="summarizing", progress="Writing summary and lecture notes…", title=title)
        _write(item_dir, meta)
        try:
            summary = await NotebookSummarizeAgent().summarize(title=title, record_type="lecture", user_query="Summarize this recorded lecture into structured study notes.", output=transcript, metadata={"source": "media_library"})
        except Exception:
            summary = transcript[:1600].strip() or "No speech was detected."
        notes = f"# {title}\n\n## Summary and study notes\n\n{summary}\n\n## Full transcript\n\n{transcript}\n"
        transcript_path = item_dir / "transcript.txt"
        notes_path = item_dir / "notes.md"
        vtt_path = item_dir / "subtitles.vtt"
        transcript_path.write_text(transcript, encoding="utf-8")
        notes_path.write_text(notes, encoding="utf-8")
        vtt_path.write_text(vtt_content, encoding="utf-8")
        meta.update(status="indexing", progress="Adding notes to the knowledge base…", summary=summary, transcript_file=transcript_path.name, notes_file=notes_path.name, subtitle_file=vtt_path.name)
        _write(item_dir, meta)
        task_id = await _index_notes(str(meta.get("kb_name") or ""), notes_path)
        meta.update(status="ready", progress="Ready", kb_task_id=task_id, completed_at=datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        meta.update(status="failed", progress=str(exc))
    _write(item_dir, meta)


def _safe_media_title(source: Echo360Source) -> str:
    title = re.sub(r'[\\/*?:"<>|]', "_", source.title).strip(" ._")
    prefix = f"{source.date} - " if source.date else ""
    return f"{prefix}{title or 'Echo360 lecture'}.mp4"


def _validated_echo360_media_url(raw_url: str) -> str:
    """Allow only Echo360's expected HTTPS media hosts; reject arbitrary URLs."""
    parsed = urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    allowed = (
        hostname == "echo360.net.au"
        or hostname.endswith(".echo360.net.au")
        or hostname.endswith(".amazonaws.com")
        or hostname.endswith(".cloudfront.net")
    )
    if parsed.scheme != "https" or not hostname or parsed.username or not allowed:
        raise HTTPException(422, "The browser returned an unsupported Echo360 media URL.")
    return raw_url


def _download_echo360_media(source: Echo360Source, destination: Path) -> None:
    """Download a browser-resolved source without accessing a browser cookie store."""
    media_url = _validated_echo360_media_url(source.media_url)
    if source.media_kind == "mp4":
        with requests.get(
            media_url,
            stream=True,
            timeout=(20, 120),
            allow_redirects=True,
            headers={"User-Agent": "DeepTurtol/1.0"},
        ) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
        if not destination.exists() or destination.stat().st_size == 0:
            raise RuntimeError("Echo360 returned an empty media file.")
        return

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            ffmpeg = get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            ffmpeg = None
    if not ffmpeg:
        raise RuntimeError(
            "This lecture is available only as an HLS stream and requires FFmpeg. "
            "Install FFmpeg once, then retry the import."
        )
    command = [
        ffmpeg,
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
    ]
    command.extend(["-i", media_url, "-c", "copy", str(destination)])
    completed = subprocess.run(
        command,
        capture_output=True,
        timeout=60 * 60 * 4,
        check=False,
    )
    if completed.returncode != 0 or not destination.exists():
        detail = completed.stderr.decode("utf-8", errors="replace")[-500:].strip()
        raise RuntimeError(f"FFmpeg could not download this lecture. {detail}")


async def _download_and_process_echo360(
    item_id: str,
    source: Echo360Source,
) -> None:
    """Background import of a source resolved in the normal browser session."""
    item_dir = _root() / item_id
    meta = _read(item_dir)
    try:
        meta.update(
            status="downloading",
            progress="Downloading the selected UniMelb Echo360 recording…",
        )
        _write(item_dir, meta)
        await asyncio.to_thread(
            _download_echo360_media,
            source,
            item_dir / meta["media_file"],
        )
        await _process(item_id)
    except Exception as exc:
        meta = _read(item_dir)
        meta.update(status="failed", progress=str(exc))
        _write(item_dir, meta)


def _existing_echo360_ids() -> set[str]:
    ids: set[str] = set()
    for item_dir in _root().iterdir():
        if not item_dir.is_dir() or not (item_dir / "metadata.json").exists():
            continue
        meta = _read(item_dir)
        if meta.get("source") == "echo360" and meta.get("source_id"):
            ids.add(str(meta["source_id"]))
    return ids


@router.get("")
async def list_library() -> dict[str, list[dict]]:
    items = [_read(p) for p in _root().iterdir() if p.is_dir() and (p / "metadata.json").exists()]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": items}


@router.post("")
async def create_library_item(background_tasks: BackgroundTasks, file: UploadFile = File(...), kb_name: str = Form("")) -> dict:
    content_type = (
        file.content_type
        or mimetypes.guess_type(file.filename or "")[0]
        or "application/octet-stream"
    ).partition(";")[0].strip().lower()
    if content_type not in _MEDIA_TYPES:
        raise HTTPException(415, "Upload an MP3, WAV, WebM, MP4, or MOV recording.")
    item_id = uuid4().hex
    item_dir = _root() / item_id
    item_dir.mkdir(parents=True)
    suffix = Path(file.filename or "recording.webm").suffix.lower() or ".webm"
    media_name = f"media{suffix}"
    (item_dir / media_name).write_bytes(await file.read())
    meta = {"id": item_id, "title": Path(file.filename or "Lecture").stem, "original_name": file.filename or "recording.webm", "content_type": content_type, "media_file": media_name, "kb_name": kb_name, "status": "queued", "progress": "Queued", "created_at": datetime.now(timezone.utc).isoformat()}
    _write(item_dir, meta)
    background_tasks.add_task(_process, item_id)
    return meta


@router.get("/echo360/connector-version")
async def echo360_connector_version() -> dict[str, str]:
    """Return the current userscript version so the WebUI can prompt updates."""
    source = files("deeptutor").joinpath(
        "assets", "echo360_userscript", "echo360-connector.user.js"
    )
    text = source.read_text(encoding="utf-8")
    m = re.search(r"@version\s+(\S+)", text)
    return {"version": m.group(1) if m else "0.0.0"}


@router.get("/echo360/connector.user.js", response_class=PlainTextResponse)
async def download_echo360_connector() -> PlainTextResponse:
    """Serve the Tampermonkey connector; no browser extension bundle is used."""
    source = files("deeptutor").joinpath(
        "assets", "echo360_userscript", "echo360-connector.user.js"
    )
    return PlainTextResponse(
        source.read_text(encoding="utf-8"),
        media_type="text/javascript; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="deepturtol-echo360.user.js"'},
    )


@router.post("/echo360/import")
async def import_echo360_course(
    payload: Echo360ImportRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Queue browser-resolved sources into the normal media-library pipeline."""
    existing = _existing_echo360_ids()
    queued: list[dict[str, Any]] = []
    skipped = 0
    for source in payload.sources:
        if source.course_id != payload.course_id:
            raise HTTPException(422, "Every selected recording must belong to the selected course.")
        _validated_echo360_media_url(source.media_url)
        if source.id in existing:
            skipped += 1
            continue
        item_id = uuid4().hex
        item_dir = _root() / item_id
        item_dir.mkdir(parents=True)
        original_name = _safe_media_title(source)
        meta = {
            "id": item_id,
            "title": source.title,
            "original_name": original_name,
            "content_type": "video/mp4",
            "media_file": "media.mp4",
            "kb_name": payload.kb_name,
            "status": "queued",
            "progress": "Queued from UniMelb Echo360",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "echo360",
            "source_id": source.id,
            # The resolved URL can be short-lived; do not persist it in metadata.
            "source_url": f"https://echo360.net.au/lesson/{source.id}/classroom",
            "institution": "University of Melbourne",
            "course_id": payload.course_id,
            "course_name": source.course_name,
            "lecture_date": source.date,
        }
        _write(item_dir, meta)
        background_tasks.add_task(
            _download_and_process_echo360,
            item_id,
            source,
        )
        queued.append(meta)
        existing.add(source.id)
    return {"queued": queued, "skipped": skipped}


@router.get("/{item_id}")
async def get_library_item(item_id: str) -> dict:
    return _read(_root() / item_id)


@router.get("/{item_id}/media")
async def stream_library_media(item_id: str) -> FileResponse:
    item_dir = _root() / item_id
    meta = _read(item_dir)
    return FileResponse(item_dir / meta["media_file"], media_type=meta["content_type"], filename=meta["original_name"])


@router.get("/{item_id}/subtitles")
async def get_library_subtitles(item_id: str):
    item_dir = _root() / item_id
    meta = _read(item_dir)
    filename = meta.get("subtitle_file")
    if not filename:
        raise HTTPException(404, "Subtitles are not ready.")
    return PlainTextResponse(
        (item_dir / filename).read_text(encoding="utf-8"),
        media_type="text/vtt; charset=utf-8",
    )


@router.get("/{item_id}/{artifact}")
async def get_library_artifact(item_id: str, artifact: str) -> PlainTextResponse:
    if artifact not in {"transcript", "notes"}:
        raise HTTPException(404, "Artifact not found.")
    item_dir = _root() / item_id
    meta = _read(item_dir)
    filename = meta.get(f"{artifact}_file")
    if not filename:
        raise HTTPException(404, f"{artifact.title()} is not ready.")
    return PlainTextResponse((item_dir / filename).read_text(encoding="utf-8"))
