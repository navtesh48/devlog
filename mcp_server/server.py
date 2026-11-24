"""MCP server: gives Claude Code, Cursor, ChatGPT, etc. one shared project memory.

Add to an MCP client config:
    {"mcpServers": {"devlog": {"command": "python", "args": ["mcp_server/server.py"],
                               "env": {"DEVLOG_API": "http://localhost:8080", "DEVLOG_PROJECT": "my-app"}}}}
"""
from __future__ import annotations

import os

import requests
from mcp.server.fastmcp import FastMCP

API = os.getenv("DEVLOG_API", "http://localhost:8080").rstrip("/")
PROJECT = os.getenv("DEVLOG_PROJECT", "default")

mcp = FastMCP("devlog")


@mcp.tool()
def read_log(limit: int = 30) -> str:
    """Read the most recent entries of the shared project log (newest first).
    Call this at the start of a task to learn what other agents and the developer already did."""
    r = requests.get(f"{API}/logs", params={"project": PROJECT, "limit": limit}, timeout=10)
    r.raise_for_status()
    rows = r.json()["entries"]
    if not rows:
        return "The log is empty."
    return "\n".join(f"[{e['kind']}/{e['category']}] {e['author']}: {e['summary']}" +
                     (f" ({e['path']})" if e.get("path") else "") for e in rows)


@mcp.tool()
def record_decision(summary: str, author: str = "agent") -> str:
    """Record an important decision or note so every other agent on the project can see it."""
    r = requests.post(f"{API}/notes", timeout=10,
                      json={"project": PROJECT, "kind": "decision", "summary": summary, "author": author})
    r.raise_for_status()
    return f"Recorded: {summary}"


if __name__ == "__main__":
    mcp.run()
