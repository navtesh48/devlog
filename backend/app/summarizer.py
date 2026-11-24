"""Turns a raw diff into a plain-English summary and a category using Gemini.

If no GEMINI_API_KEY is configured (local dev, CI) a deterministic heuristic is
used so the rest of the pipeline still works end to end.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

CATEGORIES = ["feature", "bugfix", "refactor", "docs", "test", "config", "other"]

PROMPT = """You are a developer's logbook. Given a unified diff, reply with JSON only:
{{"category": one of {cats}, "summary": "<one plain-English sentence, max 25 words, say WHAT changed and WHY if obvious>"}}

File: {path}
Change: {change}
Diff:
{diff}
"""


@dataclass
class Summary:
    category: str
    summary: str


def _heuristic(path: str, change: str, diff: str) -> Summary:
    added = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    lower = path.lower()
    if "test" in lower:
        cat = "test"
    elif lower.endswith((".md", ".rst", ".txt")):
        cat = "docs"
    elif lower.endswith((".json", ".yml", ".yaml", ".toml", ".ini", ".env")):
        cat = "config"
    elif change == "created":
        cat = "feature"
    elif re.search(r"\b(fix|bug|error|crash)\b", diff, re.I):
        cat = "bugfix"
    else:
        cat = "other"
    verb = {"created": "Created", "deleted": "Deleted"}.get(change, "Modified")
    return Summary(cat, f"{verb} {path} (+{added}/-{removed} lines).")


class Summarizer:
    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        self.model = model
        self._client = None
        key = os.getenv("GEMINI_API_KEY")
        if key:
            from google import genai

            self._client = genai.Client(api_key=key)

    def summarize(self, path: str, change: str, diff: str) -> Summary:
        if self._client is None:
            return _heuristic(path, change, diff)
        prompt = PROMPT.format(cats=CATEGORIES, path=path, change=change, diff=diff[:12000])
        try:
            resp = self._client.models.generate_content(model=self.model, contents=prompt)
            text = re.sub(r"^```(?:json)?|```$", "", resp.text.strip(), flags=re.M).strip()
            data = json.loads(text)
            cat = data.get("category", "other")
            return Summary(cat if cat in CATEGORIES else "other", str(data["summary"]).strip())
        except Exception:  # network/quota/parse errors must never drop an event
            return _heuristic(path, change, diff)
