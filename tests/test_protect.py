import asyncio

from gatekeeper import protect
from gatekeeper.presets import PRESETS

P = {p["id"]: p["html"] for p in PRESETS}


def test_protect_blocks_attack_and_passes_clean():
    @protect
    def read(page_id):
        return P[page_id]
    assert read("comment").startswith("[BLOCKED by Gatekeeper]")
    out = read("clean")
    assert "₹780" in out and "BLOCKED" not in out


def test_protect_keeps_function_metadata():
    @protect
    def read_page(url):
        """Fetch a page."""
        return ""
    assert read_page.__name__ == "read_page" and read_page.__doc__ == "Fetch a page."


def test_protect_options_and_callback():
    seen = []
    @protect(max_chars=10, on_result=seen.append)
    def read():
        return "<p>" + "x" * 100 + "</p>"
    assert len(read()) == 10 and seen and seen[0].decision == "pass"


def test_protect_handles_non_string_results():
    @protect
    def search():
        return [{"title": "ok", "snippet": "hello"}]
    assert "hello" in search()


def test_protect_async():
    @protect
    async def read():
        return P["css"]
    assert asyncio.run(read()).startswith("[BLOCKED")


def test_protect_uses_layer3_when_given():
    @protect(llm=lambda t: {"verdict": "malicious", "reason": "x"})
    def read():
        return P["article"]
    assert read().startswith("[BLOCKED")
