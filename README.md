# DevLog: Real-Time Memory Layer for AI Coding Agents

> **Provenance:** a clean reimplementation of a project I originally built (it won the Google Track at Innovation Hacks 2.0); the original code was unavailable, so this was rebuilt from the original design. The backend tests pass, but I have **not** run it against live Gemini, Firestore or Cloud Run, and the watcher, MCP server, dashboard and VSCode extension have only been syntax-checked. The ElevenLabs voice integration from the demo is not included.

🏆 **Winner, Google Track, Innovation Hacks 2.0 (Apr 2026)**

`Python` `FastAPI` `Gemini` `Firestore` `React` `MCP` `ElevenLabs`

DevLog watches file changes as you code, uses Gemini to summarize each diff in plain English, and streams the running log to a React dashboard and a VSCode extension. The same log is exposed through an **MCP server**, so Claude Code, Cursor, ChatGPT and any other MCP-capable tool read and write one shared record of decisions and code changes.

```
 your editor ──save──▶ watcher ──POST /events──▶ FastAPI (Cloud Run) ──▶ Gemini summary
                                                        │                    │
                                                        ▼                    ▼
                                                    Firestore ◀──────── LogEntry
                                                        │
              ┌─────────────────────┬───────────────────┴──────────────┐
              ▼                     ▼                                  ▼
       React dashboard      VSCode extension                   MCP server (read_log,
       (SSE live feed)      (live Output log)                  record_decision)
```

## Repo layout
| Path | What it is |
|---|---|
| `backend/` | FastAPI service: ingests events, calls Gemini, stores in Firestore (memory store for local dev), streams via SSE. Dockerfile for Cloud Run. |
| `watcher/` | File watcher that diffs each save against the previous snapshot and posts it to the API. |
| `mcp_server/` | MCP server exposing `read_log` and `record_decision` to external AI tools. |
| `dashboard/` | React (Vite) live dashboard with category filters. |
| `vscode-extension/` | VSCode extension showing the live log in-editor. |

## Quick start
```bash
# 1. API (works without a Gemini key using a heuristic summarizer)
cd backend && pip install -r requirements.txt
export GEMINI_API_KEY=...        # optional
uvicorn app.main:app --port 8080

# 2. Watch a project
cd ../watcher && pip install -r requirements.txt
python watcher.py ~/code/my-app --project my-app

# 3. Dashboard
cd ../dashboard && npm install && npm run dev
```

### Connect an AI coding tool (MCP)
```json
{
  "mcpServers": {
    "devlog": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "env": { "DEVLOG_API": "http://localhost:8080", "DEVLOG_PROJECT": "my-app" }
    }
  }
}
```
Agents can then call `read_log` before starting work and `record_decision` after making a call, so the next agent (or you) knows why.

## Deploy
```bash
gcloud run deploy devlog-api --source backend --set-env-vars DEVLOG_STORE=firestore,GEMINI_API_KEY=...
```

## Tests
```bash
cd backend && pytest
```

## Notes
This repository is a clean, documented reimplementation of the hackathon project's architecture. The ElevenLabs voice-readout integration from the demo is not included.
