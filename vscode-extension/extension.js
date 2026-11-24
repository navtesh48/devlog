// Streams the DevLog SSE feed into an Output channel and a status-bar counter.
const vscode = require("vscode");
const http = require("http");
const https = require("https");

let req, count = 0;

function connect(out, status) {
  const cfg = vscode.workspace.getConfiguration("devlog");
  const url = new URL(`${cfg.get("api")}/logs/stream?project=${encodeURIComponent(cfg.get("project"))}`);
  const lib = url.protocol === "https:" ? https : http;
  req = lib.get(url, (res) => {
    let buf = "";
    res.setEncoding("utf8");
    res.on("data", (chunk) => {
      buf += chunk;
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const frame = buf.slice(0, i);
        buf = buf.slice(i + 2);
        if (!frame.startsWith("data: ")) continue;
        const e = JSON.parse(frame.slice(6));
        count += 1;
        status.text = `$(history) DevLog ${count}`;
        const t = new Date(e.created_at * 1000).toLocaleTimeString();
        out.appendLine(`${t}  [${e.kind === "decision" ? "decision" : e.category}] ${e.author}: ${e.summary}`);
      }
    });
    res.on("end", () => setTimeout(() => connect(out, status), 3000));
  });
  req.on("error", () => setTimeout(() => connect(out, status), 3000));
}

function activate(context) {
  const out = vscode.window.createOutputChannel("DevLog");
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left);
  status.text = "$(history) DevLog";
  status.command = "devlog.openLog";
  status.show();

  context.subscriptions.push(
    out, status,
    vscode.commands.registerCommand("devlog.openLog", () => out.show(true)),
    vscode.commands.registerCommand("devlog.addNote", async () => {
      const summary = await vscode.window.showInputBox({ prompt: "Decision or note for the shared log" });
      if (!summary) return;
      const cfg = vscode.workspace.getConfiguration("devlog");
      await fetch(`${cfg.get("api")}/notes`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ project: cfg.get("project"), summary, author: "developer" }),
      });
    })
  );
  connect(out, status);
}

function deactivate() { if (req) req.destroy(); }

module.exports = { activate, deactivate };
