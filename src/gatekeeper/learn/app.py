"""Learn Mode: a small local web app (runs on your own computer, nothing is hosted)."""
from pathlib import Path

from flask import Flask, Response, jsonify, request

from ..core import scan_html
from ..layer3 import layer3_status
from ..presets import PRESETS
from ..scorer import BLOCK_MIN, PASS_MAX

INDEX = Path(__file__).with_name("index.html")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 300_000

    @app.get("/")
    def index():
        return Response(INDEX.read_text(encoding="utf-8"), mimetype="text/html")

    @app.get("/api/presets")
    def presets():
        return jsonify(PRESETS)

    @app.get("/api/status")
    def status():
        return jsonify(layer3=layer3_status(), pass_max=PASS_MAX, block_min=BLOCK_MIN)

    @app.post("/api/scan")
    def scan():
        html = (request.get_json(silent=True) or {}).get("html", "")
        if not isinstance(html, str) or not html.strip():
            return jsonify(error="Paste some HTML to scan."), 400
        r = scan_html(html)
        return jsonify(
            decision=r.decision,
            score=r.score,
            signals=[{"name": s.name, "points": s.points, "evidence": s.evidence} for s in r.signals],
            lessons=r.lessons(),
            visible_text=r.visible_text,
            hidden_parts=r.hidden_parts,
            clean_text=r.clean_text,
            note=r.note,
            ai_check=r.llm_verdict,
            layer3=layer3_status(),
            pass_max=PASS_MAX,
            block_min=BLOCK_MIN,
        )

    return app
