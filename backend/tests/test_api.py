from fastapi.testclient import TestClient

from app.main import app, get_store
from app.store import MemoryStore
from app.summarizer import Summarizer


def make_client():
    store = MemoryStore()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_event_is_summarized_and_stored():
    c = make_client()
    r = c.post("/events", json={"path": "src/app.py", "change": "modified",
                                "diff": "+++ b\n-fix\n+def fixed(): pass\n"})
    assert r.status_code == 200
    assert r.json()["summary"]
    logs = c.get("/logs").json()["entries"]
    assert len(logs) == 1 and logs[0]["path"] == "src/app.py"


def test_notes_are_shared_with_log():
    c = make_client()
    c.post("/notes", json={"summary": "Use Firestore, not Postgres", "author": "claude-code"})
    entries = c.get("/logs").json()["entries"]
    assert entries[0]["kind"] == "decision"
    assert entries[0]["author"] == "claude-code"


def test_projects_are_isolated():
    c = make_client()
    c.post("/notes", json={"project": "a", "summary": "x"})
    assert c.get("/logs", params={"project": "b"}).json()["entries"] == []


def test_heuristic_categories():
    s = Summarizer()
    assert s.summarize("tests/test_x.py", "modified", "+a").category == "test"
    assert s.summarize("README.md", "modified", "+a").category == "docs"
    assert s.summarize("a.py", "created", "+a").category == "feature"
