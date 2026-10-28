"""Gatekeeper: check what your AI agent reads before it acts."""
from .core import AUTO, ScanResult, protect, safe_fetch, scan_html

__all__ = ["protect", "safe_fetch", "scan_html", "ScanResult", "AUTO"]
__version__ = "0.1.0"
