import json

import gatekeeper.layer3 as l3
from gatekeeper import scan_html
from gatekeeper.presets import PRESETS

ARTICLE = next(p["html"] for p in PRESETS if p["id"] == "article")


class Resp:
    def __init__(self, data, ok=True):
        self._d, self._ok = data, ok
    def raise_for_status(self):
        if not self._ok:
            raise RuntimeError("bad")
    def json(self):
        return self._d


def test_status_values(monkeypatch):
    assert l3.layer3_status() == "not configured"
    monkeypatch.setenv("GATEKEEPER_L3_URL", "https://x.example/check")
    assert l3.layer3_status() == "on"
    monkeypatch.setenv("GATEKEEPER_LAYER3", "off")
    assert l3.layer3_status() == "off" and l3.default_llm() is None


def test_remote_judge_success_notice_once_and_truncation(monkeypatch, capsys):
    monkeypatch.setenv("GATEKEEPER_L3_URL", "https://x.example/check")
    sent = []
    monkeypatch.setattr(l3.requests, "post", lambda url, json, timeout: sent.append((url, json)) or Resp({"verdict": "safe", "reason": "ok"}))
    assert l3.remote_judge("a" * 20000)["verdict"] == "safe"
    l3.remote_judge("again")
    assert len(sent[0][1]["text"]) == l3.MAX_CHARS
    err = capsys.readouterr().err
    assert err.count("Layer 3 is on") == 1 and "GATEKEEPER_LAYER3=off" in err


def test_remote_judge_failures_return_none(monkeypatch):
    monkeypatch.setenv("GATEKEEPER_L3_URL", "https://x.example/check")
    monkeypatch.setattr(l3.requests, "post", lambda *a, **k: Resp({"verdict": "unavailable"}))
    assert l3.remote_judge("x") is None
    def boom(*a, **k):
        raise TimeoutError()
    monkeypatch.setattr(l3.requests, "post", boom)
    assert l3.remote_judge("x") is None


def test_default_layer3_used_by_scan_html(monkeypatch):
    monkeypatch.setenv("GATEKEEPER_L3_URL", "https://x.example/check")
    monkeypatch.setattr(l3.requests, "post", lambda *a, **k: Resp({"verdict": "malicious", "reason": "injection"}))
    r = scan_html(ARTICLE)
    assert r.blocked and r.llm_verdict["reason"] == "injection"


def test_service_down_falls_back_to_local_layers(monkeypatch):
    monkeypatch.setenv("GATEKEEPER_L3_URL", "https://x.example/check")
    monkeypatch.setattr(l3.requests, "post", lambda *a, **k: (_ for _ in ()).throw(TimeoutError()))
    r = scan_html(ARTICLE)
    assert r.decision == "check" and "unavailable" in r.note


def test_client_judge_with_openai_style_client():
    class Msg: content = '```json\n{"verdict": "suspicious", "reason": "hmm"}\n```'
    class Choice: message = Msg()
    class Completions:
        def create(self, **kw): return type("R", (), {"choices": [Choice()]})()
    class Chat: completions = Completions()
    class Client: chat = Chat()
    assert l3.client_judge(Client(), "m")("text")["verdict"] == "suspicious"
    class Broken:
        class chat:
            class completions:
                @staticmethod
                def create(**kw): raise RuntimeError("down")
    assert l3.client_judge(Broken(), "m")("text") is None
