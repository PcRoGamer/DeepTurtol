import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from deeptutor.api.routers import lectures


def test_library_persists_media_and_generated_artifacts(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)

    async def transcribe(*args, **kwargs):
        return json.dumps({
            "text": "Fourier transforms convert signals into frequency components.",
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "Fourier transforms convert signals"},
                {"start": 1.5, "end": 3.0, "text": "into frequency components."},
            ],
        })

    async def summarize(self, **kwargs):
        return "Fourier transforms reveal the frequency content of signals."

    async def index_notes(kb_name, notes_path):
        assert notes_path.exists()
        return "kb-task-1"

    monkeypatch.setattr(lectures, "transcribe_audio", transcribe)
    monkeypatch.setattr(lectures.NotebookSummarizeAgent, "summarize", summarize)
    monkeypatch.setattr(lectures, "_index_notes", index_notes)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)

    response = client.post(
        "/api/v1/lectures",
        data={"kb_name": "physics"},
        files={"file": ("week-1.webm", b"audio", "audio/webm;codecs=opus")},
    )
    assert response.status_code == 200
    item_id = response.json()["id"]
    item = client.get(f"/api/v1/lectures/{item_id}").json()
    assert item["status"] == "ready"
    assert item["title"].startswith("Fourier transforms")
    assert client.get(f"/api/v1/lectures/{item_id}/media").content == b"audio"
    assert "frequency content" in client.get(f"/api/v1/lectures/{item_id}/notes").text
    assert "frequency components" in client.get(f"/api/v1/lectures/{item_id}/transcript").text

    # Check subtitles.
    subs = client.get(f"/api/v1/lectures/{item_id}/subtitles")
    assert subs.status_code == 200
    assert subs.headers["content-type"] == "text/vtt; charset=utf-8"
    assert "WEBVTT" in subs.text
    assert "00:00:00.000 --> 00:00:01.500" in subs.text
    assert "Fourier transforms convert signals" in subs.text


def test_library_rejects_unsupported_upload(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)
    response = client.post(
        "/api/v1/lectures",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_echo360_import_enters_normal_library_pipeline(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)

    def download(source, destination):
        destination.write_bytes(b"video")

    async def transcribe(*args, **kwargs):
        return json.dumps({
            "text": "Breadth-first search explores a graph level by level.",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Breadth-first search explores a graph"},
                {"start": 2.0, "end": 3.5, "text": "level by level."},
            ],
        })

    async def summarize(self, **kwargs):
        return "A lecture about breadth-first graph traversal."

    monkeypatch.setattr(lectures, "_download_echo360_media", download)
    monkeypatch.setattr(lectures, "transcribe_audio", transcribe)
    monkeypatch.setattr(lectures.NotebookSummarizeAgent, "summarize", summarize)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)

    response = client.post(
        "/api/v1/lectures/echo360/import",
        json={
            "course_id": "12345678-1234-1234-1234-123456789abc",
            "sources": [
                {
                    "id": "87654321-4321-4321-4321-cba987654321",
                    "title": "Graph traversal",
                    "date": "2026-07-20",
                    "course_id": "12345678-1234-1234-1234-123456789abc",
                    "course_name": "COMP10001 — Foundations of Computing",
                    "media_url": "https://echo360.net.au/lecture.mp4",
                    "media_kind": "mp4",
                }
            ],
            "kb_name": "",
        },
    )

    assert response.status_code == 200
    item = response.json()["queued"][0]
    stored = client.get(f"/api/v1/lectures/{item['id']}").json()
    assert stored["source"] == "echo360"
    assert stored["institution"] == "University of Melbourne"
    assert stored["status"] == "ready"


def test_echo360_import_multi_source(tmp_path: Path, monkeypatch):
    """Import multiple Echo360 sources at once; skips duplicates."""
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)

    def download(source, destination):
        destination.write_bytes(b"video")

    async def transcribe(*args, **kwargs):
        return json.dumps({"text": "test.", "segments": [{"start": 0.0, "end": 1.0, "text": "test."}]})

    async def summarize(self, **kwargs):
        return "Lecture summary."

    monkeypatch.setattr(lectures, "_download_echo360_media", download)
    monkeypatch.setattr(lectures, "transcribe_audio", transcribe)
    monkeypatch.setattr(lectures.NotebookSummarizeAgent, "summarize", summarize)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)

    course_id = "12345678-1234-1234-1234-123456789abc"
    sources = [
        {
            "id": f"src-{i}",
            "title": f"Lecture {i}",
            "date": f"2026-07-2{i}",
            "course_id": course_id,
            "course_name": "COMP10001 — Foundations",
            "media_url": f"https://content.echo360.net.au/lecture{i}.mp4",
            "media_kind": "mp4",
        }
        for i in range(1, 4)
    ]

    response = client.post(
        "/api/v1/lectures/echo360/import",
        json={"course_id": course_id, "sources": sources, "kb_name": ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["queued"]) == 3
    assert data["skipped"] == 0

    # Second import with same IDs — all should be skipped
    response2 = client.post(
        "/api/v1/lectures/echo360/import",
        json={"course_id": course_id, "sources": sources, "kb_name": ""},
    )
    assert response2.status_code == 200
    assert response2.json()["skipped"] == 3


def test_echo360_import_rejects_non_https_media(tmp_path: Path, monkeypatch):
    """Verify _validated_echo360_media_url rejects non-https URLs."""
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)

    response = client.post(
        "/api/v1/lectures/echo360/import",
        json={
            "course_id": "12345678-1234-1234-1234-123456789abc",
            "sources": [
                {
                    "id": "src-http",
                    "title": "HTTP source",
                    "date": "2026-07-20",
                    "course_id": "12345678-1234-1234-1234-123456789abc",
                    "course_name": "Test",
                    "media_url": "http://echo360.net.au/lecture.mp4",
                    "media_kind": "mp4",
                }
            ],
            "kb_name": "",
        },
    )
    assert response.status_code == 422
    assert "unsupported" in response.json()["detail"].lower()


def test_echo360_import_rejects_unrelated_course(tmp_path: Path, monkeypatch):
    """Every source must belong to the posted course_id."""
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)

    response = client.post(
        "/api/v1/lectures/echo360/import",
        json={
            "course_id": "11111111-1111-1111-1111-111111111111",
            "sources": [
                {
                    "id": "src-mismatch",
                    "title": "Wrong course",
                    "date": "2026-07-20",
                    "course_id": "22222222-2222-2222-2222-222222222222",
                    "course_name": "Other",
                    "media_url": "https://content.echo360.net.au/lecture.mp4",
                    "media_kind": "mp4",
                }
            ],
            "kb_name": "",
        },
    )
    assert response.status_code == 422
    assert "belong" in response.json()["detail"].lower()


def test_library_subtitles_404_on_missing_item(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(lectures, "_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(lectures.router, prefix="/api/v1/lectures")
    client = TestClient(app)
    resp = client.get("/api/v1/lectures/00000000000000000000000000000000/subtitles")
    assert resp.status_code == 404
