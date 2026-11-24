"""Pydantic models shared by the API, store and MCP server."""
from __future__ import annotations

import time
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class FileEvent(BaseModel):
    """A single file change reported by the watcher."""

    project: str = "default"
    path: str
    change: str = Field("modified", description="created | modified | deleted")
    diff: str = ""
    author: str = "watcher"


class LogEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    project: str = "default"
    path: Optional[str] = None
    kind: str = Field("change", description="change | decision | note")
    category: str = "other"  # feature | bugfix | refactor | docs | test | config | other
    summary: str
    author: str = "watcher"
    created_at: float = Field(default_factory=time.time)


class NoteIn(BaseModel):
    """Used by external agents (via MCP) to record a decision or note."""

    project: str = "default"
    kind: str = "decision"
    summary: str
    author: str = "agent"


class LogPage(BaseModel):
    entries: List[LogEntry]
