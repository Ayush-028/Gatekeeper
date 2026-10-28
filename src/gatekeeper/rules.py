"""Layer 1: rule-based scan. Finds signals; layer 2 (scorer.py) turns them into a score."""
import html
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Comment

from .normalize import count_suspicious_invisible, decode_base64_blobs, normalize


@dataclass
class Signal:
    name: str
    points: int
    evidence: str


@dataclass
class Analysis:
    signals: list = field(default_factory=list)
    full_text: str = ""        # everything an agent could read, hidden parts included
    visible_text: str = ""     # what a person sees
    hidden_parts: list = field(default_factory=list)   # [{"kind": ..., "text": ...}]


# ---- phrase lists (edit these to tune detection) ----
AI_PHRASES = {
    "override": r"(ignore|disregard|forget|override)\W+(?:\w+\W+){0,3}(previous|prior|above|earlier|system)\W+(instructions?|prompts?|rules?|messages?)",
    "override_user": r"(ignore|disregard)\W+(the\W+)?(user'?s?\W+)?(budget|request|task|question|price|prices|limit|goal)",
    "role_change": r"you\s+are\s+now\b|new\s+instructions?\s*:|act\s+as\s+(an?\s+)?(admin|developer|system)|\bsystem\s+(notice|override|message)\b",
    "secrecy": r"(do\s+not|don't|never)\s+(tell|inform|mention|show)\s+(this\s+to\s+)?(the\s+)?user",
    "addressing_ai": r"(attention|note\s+to|message\s+for|instructions?\s+for)\s+(the\s+)?(ai|assistant|agent|llm|model|chatbot)|if\s+you\s+are\s+an?\s+(ai|assistant|llm)",
}
SECRET_REQUEST = r"(reveal|print|output|include|send|post|upload|leak|share|repeat|give)\W+(?:\w+\W+){0,6}(secret|api\W?key|password|token|credential|private\s+key|canary)"
SEND_TO_URL = r"(send|post|upload|forward|submit)\W+(?:\w+\W+){0,8}https?://"
# Wording that only counts when it appears in HIDDEN content (comments, hidden CSS, decoded text).
# Normal pages talk about "AI assistants" and "the cheapest prices" openly, so we don't flag them in visible text.
HIDDEN_AIMED = {
    "aimed_at_ai": r"\b(ai|llm|automated|language\s+model)\s+(?:\w+\s+){0,2}(assistants?|agents?|bots?|models?|crawlers?)\b"
                   r"|\b(shopping|comparison|research|browsing|price[-\s]?comparison)\s+(assistants?|agents?|bots?)\b"
                   r"|\b(assistants?|agents?|bots?|llms?)\s+(processing|reading|parsing|summari[sz]ing|comparing|visiting)\b",
    "steering": r"\b(is|are)\s+(currently\s+)?the\s+(cheapest|lowest|best)\b"
                r"|\brecommend\s+(this|that|our|the)\s+(store|shop|site|seller|page)\b"
                r"|\bprice[-\s]?match\w*"
                r"|\b(other|competitors?'?)\s+(stores?|sites?|prices?)\b.{0,50}\b(outdated|stale|inaccurate|old)\b"
                r"|\b(do\s+not|don't|never)\s+(mention|reveal|disclose)\b",
}
LONG_COMMENT_WORDS = 12   # a comment this long is prose, not a developer label like "<!-- footer -->"
COMMENT_WORDS = r"\b(ignore|disregard|reveal|instructions?|assistant|ai|llm|secret|password|system\s+prompt)\b"

HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(px|pt|em|rem)?\s*(;|$)"
    r"|font-size\s*:\s*[01]px|opacity\s*:\s*0(\.0+)?\s*(;|$)"
    r"|(left|top|text-indent)\s*:\s*-\d{3,}"
    r"|clip\s*:\s*rect\(\s*0|clip-path\s*:\s*inset\(\s*50%",
    re.I,
)
# fine print: 2px to 10px. Only suspicious when the tiny text also carries attack wording.
TINY_STYLE = re.compile(r"font-size\s*:\s*(?:[2-9]|10)(?:\.\d+)?\s*(?:px|pt)\b", re.I)
TEXT_ATTRS = ("alt", "title", "aria-label", "content", "placeholder")
JUNK_TAGS = ["script", "style", "noscript", "template"]


def _stylesheet_sets(soup):
    """Elements hidden or made tiny by rules in <style> blocks (classes, ids, tags), not just inline style."""
    hidden, tiny = set(), set()
    css = "\n".join(s.get_text() for s in soup.find_all("style"))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for selectors, decl in re.findall(r"([^{}@]+)\{([^{}]*)\}", css):
        target = hidden if HIDDEN_STYLE.search(decl) else tiny if TINY_STYLE.search(decl) else None
        if target is None:
            continue
        for sel in selectors.split(","):
            sel = sel.strip()
            if not sel or "::" in sel or ":before" in sel or ":after" in sel:
                continue
            try:
                for el in soup.select(sel):
                    target.add(id(el))
            except Exception:
                pass
    return hidden, tiny


def _looks_like_prose(comment: str) -> bool:
    """Long comment made of ordinary words (a note to a reader), not a machine report full of numbers and settings."""
    words = comment.split()
    if len(words) < LONG_COMMENT_WORDS:
        return False
    alpha = sum(w.strip(".,;:!?()'\"-").isalpha() for w in words)
    return alpha / len(words) >= 0.8


def _aimed(text: str) -> bool:
    return bool(match_phrases(text) or match_hidden_aimed(text) or match_secret_request(text))


def _inspect(soup):
    """Return (hidden_roots, faint_roots). Call BEFORE <style> tags are removed.

    hidden: elements hidden with inline style OR a stylesheet rule.
    faint:  tiny-text elements whose text addresses an AI (legal fine print without attack wording is left alone).
    """
    css_hidden, css_tiny = _stylesheet_sets(soup)

    def hidden(el):
        return bool(el.has_attr("hidden") or HIDDEN_STYLE.search(el.get("style", "") or "") or id(el) in css_hidden)

    def tiny(el):
        return bool(TINY_STYLE.search(el.get("style", "") or "") or id(el) in css_tiny)

    roots, faint = [], []
    for el in soup.find_all(True):
        if hidden(el) and not any(hidden(p) for p in el.parents if p.name):
            roots.append(el)
    for el in soup.find_all(True):
        if tiny(el) and not hidden(el) and not any(hidden(p) or tiny(p) for p in el.parents if p.name):
            if _aimed(el.get_text(" ", strip=True)):
                faint.append(el)
    return roots, faint


def match_phrases(text: str) -> list:
    text = text.lower()
    hits = []
    for category, pattern in AI_PHRASES.items():
        m = re.search(pattern, text)
        if m:
            hits.append((category, m.group(0)))
    return hits


def match_hidden_aimed(text: str) -> list:
    text = text.lower()
    return [(c, m.group(0)) for c, pat in HIDDEN_AIMED.items() if (m := re.search(pat, text))]


def match_secret_request(text: str):
    text = text.lower()
    return re.search(SECRET_REQUEST, text) or re.search(SEND_TO_URL, text)


def _short(text: str, n: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def analyze(raw_html: str) -> Analysis:
    soup = BeautifulSoup(raw_html, "html.parser")
    roots, faint = _inspect(soup)   # must run before <style> tags are removed
    hidden_texts = [normalize(el.get_text(" ", strip=True)) for el in roots + faint]
    hidden_texts = [t for t in hidden_texts if len(t) >= 3]
    for tag in soup(JUNK_TAGS):
        tag.decompose()  # agents don't read these, and code like send(token) would cause false alarms

    comments = [normalize(str(c)) for c in soup.find_all(string=lambda s: isinstance(s, Comment))]
    attr_texts = [normalize(str(el.get(a))) for el in soup.find_all(True) for a in TEXT_ATTRS if el.get(a)]
    body = soup.body or soup                  # <title> is not page content, so keep it out of "visible"
    visible = normalize(body.get_text(" "))
    title_texts = [normalize(el.get_text(" ", strip=True)) for el in soup.find_all("title")]

    base_text = " ".join([visible] + title_texts + comments + hidden_texts + attr_texts)
    decoded = decode_base64_blobs(base_text)
    hidden_blob = " ".join(comments + hidden_texts + decoded)
    full_text = " ".join([base_text] + decoded)

    hidden_parts = (
        [{"kind": "comment", "text": c} for c in comments]
        + [{"kind": "css", "text": t} for t in hidden_texts]
        + [{"kind": "decoded", "text": d} for d in decoded]
    )

    signals = []
    # Comments and hidden elements are always removed before the agent reads the page, so weak signals
    # here stay low. Only attack-like wording pushes a page toward "unsure" or "block".
    keyword_comments = [c for c in comments
                        if re.search(COMMENT_WORDS, c, re.I) or match_phrases(c) or match_hidden_aimed(c)]
    prose_comments = [c for c in comments if c not in keyword_comments and _looks_like_prose(c)]
    if keyword_comments:
        signals.append(Signal("hidden_comment", 3, _short(keyword_comments[0])))
    elif prose_comments:
        signals.append(Signal("hidden_comment", 2, _short(prose_comments[0])))
    long_hidden = [h for h in hidden_texts if len(h.split()) >= 6]   # menu labels and subtitles are normal
    if long_hidden:
        signals.append(Signal("hidden_css", 2, _short(long_hidden[0])))
    invisible = count_suspicious_invisible(html.unescape(raw_html))
    if invisible:
        signals.append(Signal("zero_width", 2, f"{invisible} invisible character(s) inside plain text"))
    if decoded:
        signals.append(Signal("encoded_text", 3, _short(decoded[0])))

    phrases = match_phrases(full_text)
    hidden_aimed = match_hidden_aimed(hidden_blob)
    if phrases or hidden_aimed:
        signals.append(Signal("ai_phrase", 4, _short((phrases or hidden_aimed)[0][1])))
    secret = match_secret_request(full_text)
    if secret:
        signals.append(Signal("secret_request", 3, _short(secret.group(0))))
    if match_phrases(hidden_blob) or hidden_aimed or match_secret_request(hidden_blob):
        signals.append(Signal("hidden_instruction", 3, "instruction-like text inside hidden content"))

    return Analysis(signals=signals, full_text=full_text, visible_text=" ".join(visible.split()),
                    hidden_parts=hidden_parts)


def clean_visible_text(raw_html: str) -> str:
    """What the agent is allowed to see: visible text only, hidden parts removed."""
    soup = BeautifulSoup(raw_html, "html.parser")
    roots, faint = _inspect(soup)
    for tag in soup(JUNK_TAGS):
        tag.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for el in roots + faint:
        if not getattr(el, "decomposed", False):
            el.decompose()
    text = normalize((soup.body or soup).get_text("\n"))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
