"""Lightweight web UI for the agent. Run: python server.py  ->  open http://127.0.0.1:5000"""
from flask import Flask, request, jsonify
from agent import run_agent

app = Flask(__name__)

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Web Agent</title>
<style>
  :root { --bg:#fff; --fg:#1a1a1a; --muted:#6b7280; --card:#f3f4f6; --user:#2563eb; --border:#e5e7eb; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#16181d; --fg:#e8e8e8; --muted:#9ca3af; --card:#23262d; --user:#3b82f6; --border:#2f333b; }
  }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, sans-serif; background:var(--bg); color:var(--fg);
         display:flex; flex-direction:column; height:100vh; }
  header { padding:14px 20px; border-bottom:1px solid var(--border); font-weight:600; }
  #chat { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:12px;
          max-width:800px; width:100%; margin:0 auto; }
  .msg { padding:10px 14px; border-radius:12px; max-width:85%; line-height:1.5; white-space:pre-wrap; word-wrap:break-word; }
  .user { background:var(--user); color:#fff; align-self:flex-end; }
  .bot { background:var(--card); align-self:flex-start; }
  .bot a { color:var(--user); }
  .steps { font-size:.8rem; color:var(--muted); margin-top:8px; }
  form { display:flex; gap:8px; padding:14px 20px; border-top:1px solid var(--border);
         max-width:800px; width:100%; margin:0 auto; }
  input { flex:1; padding:10px 14px; border-radius:10px; border:1px solid var(--border);
          background:var(--card); color:var(--fg); font-size:1rem; }
  button { padding:10px 18px; border:0; border-radius:10px; background:var(--user); color:#fff; font-size:1rem; cursor:pointer; }
  button:disabled { opacity:.5; cursor:wait; }
</style>
</head>
<body>
<header>Hola, this is Web Browsing Agent</header>
<div id="chat"></div>
<form id="form">
  <input id="q" placeholder="What should I look up?" autocomplete="off" autofocus>
  <button id="send">Send</button>
</form>
<script>
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const q = document.getElementById("q");
const send = document.getElementById("send");

const esc = s => s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const fmt = s => esc(s)
  .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
  .replace(/(https?:\/\/[^\s)<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');

function add(cls, html) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.innerHTML = html;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const task = q.value.trim();
  if (!task) return;
  q.value = "";
  add("user", esc(task));
  const wait = add("bot", "Thinking…");
  send.disabled = true;
  try {
    const r = await fetch("/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({task})
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Request failed");
    let html = fmt(data.answer || "(no answer)");
    if (data.steps && data.steps.length)
      html += '<div class="steps">🔧 ' + data.steps.map(esc).join("<br>🔧 ") + "</div>";
    wait.innerHTML = html;
  } catch (err) {
    wait.innerHTML = "⚠️ " + esc(err.message);
  }
  send.disabled = false;
  q.focus();
});
</script>
</body>
</html>
"""


@app.get("/")
def home():
    return PAGE


@app.post("/ask")
def ask():
    task = (request.get_json(silent=True) or {}).get("task", "").strip()
    if not task:
        return jsonify(error="Empty question"), 400
    steps = []
    try:
        answer = run_agent(task, on_step=steps.append)
    except Exception as e:
        return jsonify(error=str(e)), 500
    return jsonify(answer=answer, steps=steps)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
