import json

from gatekeeper.cli import main
from gatekeeper.learn.app import create_app
from gatekeeper.presets import PRESETS

EXPECT = {"clean": "pass", "comment": "block", "css": "block", "zerowidth": "block", "encoded": "block", "article": "check"}


def test_index_and_presets():
    c = create_app().test_client()
    assert c.get("/").status_code == 200 and b"Gatekeeper" in c.get("/").data
    assert [p["id"] for p in c.get("/api/presets").get_json()] == [p["id"] for p in PRESETS]
    assert c.get("/api/status").get_json()["layer3"] == "not configured"


def test_every_preset_gives_expected_decision():
    c = create_app().test_client()
    for p in PRESETS:
        r = c.post("/api/scan", json={"html": p["html"]}).get_json()
        assert r["decision"] == EXPECT[p["id"]], p["id"]
        if EXPECT[p["id"]] == "block":
            assert r["lessons"] and r["clean_text"] == ""


def test_scan_rejects_empty_input():
    c = create_app().test_client()
    assert c.post("/api/scan", json={"html": "  "}).status_code == 400
    assert c.post("/api/scan", data="nope").status_code == 400


def test_cli_scan(tmp_path, capsys):
    f = tmp_path / "p.html"
    f.write_text(next(p["html"] for p in PRESETS if p["id"] == "comment"), encoding="utf-8")
    main(["scan", str(f)])
    out = capsys.readouterr().out
    assert "BLOCK" in out and "Hidden comment caught" in out
