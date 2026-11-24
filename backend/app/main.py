"""DevLog API.

POST /events        watcher reports a file change -> Gemini summary -> store
POST /notes         agents record decisions/notes (used by the MCP server)
GET  /logs          recent entries for a project
GET  /logs/stream   Server-Sent Events feed for the dashboard / VSCode extension
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .models import FileEvent, LogEntry, LogPage, NoteIn
from .store import Store, build_store
from .summarizer import Summarizer

app = FastAPI(title="DevLog", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_store: Store = build_store()
_summarizer = Summarizer()


def get_store() -> Store:
    return _store


def get_summarizer() -> Summarizer:
    return _summarizer


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/events", response_model=LogEntry)
def ingest_event(event: FileEvent, store: Store = Depends(get_store), summarizer: Summarizer = Depends(get_summarizer)):
    s = summarizer.summarize(event.path, event.change, event.diff)
    entry = LogEntry(
        project=event.project, path=event.path, kind="change",
        category=s.category, summary=s.summary, author=event.author,
    )
    return store.add(entry)


@app.post("/notes", response_model=LogEntry)
def add_note(note: NoteIn, store: Store = Depends(get_store)):
    return store.add(LogEntry(project=note.project, kind=note.kind, summary=note.summary, author=note.author))


@app.get("/logs", response_model=LogPage)
def get_logs(project: str = "default", limit: int = 100, since: Optional[float] = None, store: Store = Depends(get_store)):
    return LogPage(entries=store.list(project, limit=limit, since=since))


@app.get("/logs/stream")
async def stream_logs(project: str = "default", store: Store = Depends(get_store)):
    async def gen():
        cursor = 0.0
        while True:
            fresh = store.list(project, limit=50, since=cursor)
            for e in reversed(fresh):  # oldest first
                cursor = max(cursor, e.created_at)
                yield f"data: {json.dumps(e.model_dump())}\n\n"
            yield ": keep-alive\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream")
