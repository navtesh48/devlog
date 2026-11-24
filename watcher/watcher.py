"""Watches a project folder and reports every saved change to the DevLog API.

    python watcher.py /path/to/project --project my-app --api http://localhost:8080
"""
from __future__ import annotations

import argparse
import difflib
import os
import time
from typing import Dict

import requests
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".idea", ".vscode"}
MAX_BYTES = 200_000


def ignored(path: str) -> bool:
    return any(part in IGNORE_DIRS for part in path.split(os.sep))


def read(path: str) -> str:
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


class Handler(FileSystemEventHandler):
    def __init__(self, root: str, project: str, api: str) -> None:
        self.root, self.project, self.api = root, project, api.rstrip("/")
        self.snapshots: Dict[str, str] = {}
        self._last: Dict[str, float] = {}
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for name in files:
                p = os.path.join(dirpath, name)
                self.snapshots[p] = read(p)

    def _send(self, path: str, change: str, diff: str) -> None:
        rel = os.path.relpath(path, self.root)
        try:
            requests.post(f"{self.api}/events", timeout=10,
                          json={"project": self.project, "path": rel, "change": change, "diff": diff})
            print(f"[devlog] {change}: {rel}")
        except requests.RequestException as e:
            print(f"[devlog] could not reach API: {e}")

    def _debounced(self, path: str) -> bool:
        now = time.time()
        if now - self._last.get(path, 0) < 0.5:
            return False
        self._last[path] = now
        return True

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory or ignored(event.src_path) or not self._debounced(event.src_path):
            return
        old, new = self.snapshots.get(event.src_path, ""), read(event.src_path)
        if old == new:
            return
        diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a", "b"))
        self.snapshots[event.src_path] = new
        self._send(event.src_path, "modified", diff)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or ignored(event.src_path):
            return
        new = read(event.src_path)
        self.snapshots[event.src_path] = new
        diff = "".join(difflib.unified_diff([], new.splitlines(True), "/dev/null", "b"))
        self._send(event.src_path, "created", diff)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory or ignored(event.src_path):
            return
        self.snapshots.pop(event.src_path, None)
        self._send(event.src_path, "deleted", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--project", default="default")
    ap.add_argument("--api", default="http://localhost:8080")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    obs = Observer()
    obs.schedule(Handler(root, a.project, a.api), root, recursive=True)
    obs.start()
    print(f"[devlog] watching {root} -> {a.api} (project={a.project})")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()


if __name__ == "__main__":
    main()
