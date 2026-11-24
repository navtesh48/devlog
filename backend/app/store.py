"""Storage backends. Firestore in production, in-memory for local dev and tests."""
from __future__ import annotations

import os
import threading
from typing import List, Optional, Protocol

from .models import LogEntry


class Store(Protocol):
    def add(self, entry: LogEntry) -> LogEntry: ...
    def list(self, project: str, limit: int = 100, since: Optional[float] = None) -> List[LogEntry]: ...


class MemoryStore:
    def __init__(self) -> None:
        self._entries: List[LogEntry] = []
        self._lock = threading.Lock()

    def add(self, entry: LogEntry) -> LogEntry:
        with self._lock:
            self._entries.append(entry)
        return entry

    def list(self, project: str, limit: int = 100, since: Optional[float] = None) -> List[LogEntry]:
        with self._lock:
            rows = [e for e in self._entries if e.project == project]
        if since is not None:
            rows = [e for e in rows if e.created_at > since]
        rows.sort(key=lambda e: e.created_at, reverse=True)
        return rows[:limit]


class FirestoreStore:
    """Persists entries in a `devlog_entries` collection."""

    def __init__(self, collection: str = "devlog_entries") -> None:
        from google.cloud import firestore  # imported lazily so tests don't need it

        self._firestore = firestore
        self._col = firestore.Client().collection(collection)

    def add(self, entry: LogEntry) -> LogEntry:
        self._col.document(entry.id).set(entry.model_dump())
        return entry

    def list(self, project: str, limit: int = 100, since: Optional[float] = None) -> List[LogEntry]:
        q = self._col.where("project", "==", project)
        if since is not None:
            q = q.where("created_at", ">", since)
        q = q.order_by("created_at", direction=self._firestore.Query.DESCENDING).limit(limit)
        return [LogEntry(**d.to_dict()) for d in q.stream()]


def build_store() -> Store:
    if os.getenv("DEVLOG_STORE", "memory") == "firestore":
        return FirestoreStore()
    return MemoryStore()
