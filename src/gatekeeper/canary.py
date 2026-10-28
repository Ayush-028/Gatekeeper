"""Layer 4: canary guard. Plant a fake secret, then watch the agent's output for it."""
import re
import secrets
from urllib.parse import urlparse


def make_canary() -> str:
    return "CANARY-" + secrets.token_hex(4)


def check_output(canary: str, output: str, allowed_domains=()) -> list:
    """Return a list of problems found in what the agent produced (empty list = fine)."""
    problems = []
    squash = lambda s: re.sub(r"[\s\-_\.]", "", s).lower()
    if canary.lower() in output.lower() or squash(canary) in squash(output):
        problems.append("The agent's output contains the secret canary value.")
    for url in re.findall(r"https?://[^\s)\"'>]+", output):
        host = urlparse(url).hostname or ""
        if not any(host == d or host.endswith("." + d) for d in allowed_domains):
            problems.append(f"The agent's output points to an unknown domain: {host}")
    return problems
