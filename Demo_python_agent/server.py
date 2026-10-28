"""Lightweight web UI for the agent. Run: python server.py  ->  open http://127.0.0.1:5000"""
from flask import Flask, request, jsonify
from agent import run_agent

app = Flask(__name__)

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Web Agent</title>
<style>
  :root {
    --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --surface:#ffffff;
    --border:#e7e5e4; --accent:#4f46e5; --on-accent:#ffffff;
    --shadow:0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.04);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg:#0f0f11; --fg:#ececec; --muted:#8b8b93; --surface:#1a1a1d;
      --border:#2a2a2f; --accent:#8b8cf5; --on-accent:#0f0f11;
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 4px 16px rgba(0,0,0,.3);
    }
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; display: flex; flex-direction: column;
    height: 100vh; height: 100dvh;
    background: var(--bg); color: var(--fg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
    font-size: 16px; line-height: 1.6; -webkit-font-smoothing: antialiased;
  }

  /* Header */
  header {
    display: flex; align-items: center; gap: 10px;
    padding: calc(14px + env(safe-area-inset-top, 0px)) 24px 14px;
    border-bottom: 1px solid var(--border);
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    font-size: .95rem; font-weight: 600; letter-spacing: -.01em;
  }
  header .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent);
  }

  /* Chat area */
  #chat {
    flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;
    padding: 28px max(20px, calc((100% - 720px) / 2));
    scroll-behavior: smooth;
  }
  #chat:empty::before {
    content: "What would you like to look up?";
    margin: auto; color: var(--muted); font-size: 1.1rem; letter-spacing: -.01em;
  }

  /* Messages */
  .msg {
    max-width: 85%; padding: 11px 16px; border-radius: 18px;
    white-space: pre-wrap; overflow-wrap: anywhere;
    animation: rise .25s ease-out;
  }
  @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  .user {
    align-self: flex-end; background: var(--accent); color: var(--on-accent);
    border-bottom-right-radius: 6px;
  }
  .bot {
    align-self: flex-start; background: var(--surface); border: 1px solid var(--border);
    border-bottom-left-radius: 6px; box-shadow: var(--shadow);
  }
  .bot a { color: var(--accent); text-underline-offset: 3px; text-decoration-thickness: 1px; }
  .bot b { font-weight: 600; }

  /* Tool steps */
  .steps {
    margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: .75rem; line-height: 1.7; color: var(--muted);
  }

  /* Input bar */
  form {
    padding: 12px max(20px, calc((100% - 720px) / 2)) calc(18px + env(safe-area-inset-bottom, 0px));
    background: linear-gradient(to top, var(--bg) 70%, transparent);
  }
  .bar {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 6px 6px 18px; border-radius: 999px;
    background: var(--surface); border: 1px solid var(--border); box-shadow: var(--shadow);
    transition: border-color .15s, box-shadow .15s;
  }
  .bar:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent);
  }
  input {
    flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
    color: var(--fg); font: inherit; padding: 8px 0;
  }
  input::placeholder { color: var(--muted); }
  button {
    display: grid; place-items: center; flex: none;
    width: 38px; height: 38px; border: 0; border-radius: 50%; cursor: pointer;
    background: var(--accent); color: var(--on-accent);
    transition: transform .15s, opacity .15s;
  }
  button:hover { transform: scale(1.06); }
  button:active { transform: scale(.96); }
  button:disabled { opacity: .35; cursor: wait; transform: none; }

  @media (max-width: 520px) {
    header { padding-left: 20px; padding-right: 20px; }
    .msg { max-width: 92%; }
  }
  @media (prefers-reduced-motion: reduce) {
    .msg { animation: none; } #chat { scroll-behavior: auto; }
  }
</style>
</head>
<body>
<header>
  <span class="dot"></span>
  <span>Hola, this is Web Browsing Agent</span>
</header>
<div id="chat"></div>
<form id="form">
  <div class="bar">
    <input id="q" placeholder="What should I look up?" autocomplete="off" autofocus>
    <button id="send" aria-label="Send">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
    </button>
  </div>
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
