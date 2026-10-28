"""Step 0: clean up tricks before the rules look at the text."""
import base64
import html
import re
import unicodedata

# characters that are invisible on screen but still readable by an AI
INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff\u00ad\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
_STRIP_TABLE = dict.fromkeys(map(ord, INVISIBLE), None)
_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")


def strip_invisible(text: str) -> str:
    return text.translate(_STRIP_TABLE)


def count_suspicious_invisible(text: str) -> int:
    """Count invisible characters sitting between plain ASCII characters.

    Hindi, Persian and emoji legitimately use zero-width joiners, but always next
    to non-ASCII characters. Invisible characters inside plain English text are
    the suspicious ones, so this avoids false alarms on Indian-language pages.
    """
    count = 0
    for i, ch in enumerate(text):
        if ch in INVISIBLE:
            before = text[i - 1] if i > 0 else " "
            after = text[i + 1] if i + 1 < len(text) else " "
            if ord(before) < 128 and ord(after) < 128:
                count += 1
    return count


def normalize(text: str) -> str:
    """Decode HTML entities, fold lookalike characters (NFKC), drop invisible characters."""
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    return strip_invisible(text)


def decode_base64_blobs(text: str) -> list:
    """Find base64 strings that decode to readable text (a common way to hide commands)."""
    found = []
    for blob in _BASE64_RE.findall(text):
        try:
            raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True)
            decoded = raw.decode("utf-8")
        except Exception:
            continue
        if len(decoded) < 12:
            continue
        letters = sum(c.isalpha() or c == " " for c in decoded) / len(decoded)
        printable = sum(c.isprintable() or c.isspace() for c in decoded) / len(decoded)
        if printable > 0.95 and letters > 0.6:
            found.append(decoded)
    return found
