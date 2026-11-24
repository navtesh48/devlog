import { useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_DEVLOG_API || "http://localhost:8080";
const CATEGORIES = ["all", "feature", "bugfix", "refactor", "docs", "test", "config", "other"];

export default function App() {
  const [project, setProject] = useState("default");
  const [entries, setEntries] = useState([]);
  const [filter, setFilter] = useState("all");
  const [live, setLive] = useState(false);

  useEffect(() => {
    setEntries([]);
    const es = new EventSource(`${API}/logs/stream?project=${encodeURIComponent(project)}`);
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false);
    es.onmessage = (m) => {
      const e = JSON.parse(m.data);
      setEntries((prev) => (prev.some((p) => p.id === e.id) ? prev : [e, ...prev]));
    };
    return () => es.close();
  }, [project]);

  const shown = useMemo(
    () => entries.filter((e) => filter === "all" || e.category === filter || e.kind === filter),
    [entries, filter]
  );

  return (
    <main>
      <header>
        <h1>DevLog</h1>
        <span className={`dot ${live ? "on" : ""}`} title={live ? "live" : "disconnected"} />
        <input value={project} onChange={(e) => setProject(e.target.value)} aria-label="project" />
      </header>
      <nav>
        {CATEGORIES.map((c) => (
          <button key={c} className={c === filter ? "active" : ""} onClick={() => setFilter(c)}>{c}</button>
        ))}
      </nav>
      <ul>
        {shown.map((e) => (
          <li key={e.id} className={e.kind}>
            <div className="meta">
              <span className="badge">{e.kind === "decision" ? "decision" : e.category}</span>
              <span>{e.author}</span>
              <time>{new Date(e.created_at * 1000).toLocaleTimeString()}</time>
            </div>
            <p>{e.summary}</p>
            {e.path && <code>{e.path}</code>}
          </li>
        ))}
        {shown.length === 0 && <li className="empty">Waiting for changes…</li>}
      </ul>
    </main>
  );
}
