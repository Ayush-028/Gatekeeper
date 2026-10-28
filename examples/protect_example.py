"""Smallest possible example. Runs offline, no API key, no agent needed.

    python examples/protect_example.py

In your own agent, put @protect on the tool that reads web pages (and make it return raw HTML).
"""
from gatekeeper import protect
from gatekeeper.presets import PRESETS

PAGES = {p["id"]: p["html"] for p in PRESETS}


@protect
def read_page(page_id):          # imagine this is requests.get(url).text
    return PAGES[page_id]


print("Normal page  ->", read_page("clean").splitlines()[:2])
print("Attack page  ->", read_page("comment")[:90], "...")
