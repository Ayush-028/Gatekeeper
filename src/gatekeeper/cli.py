"""Command line:  gatekeeper            open Learn Mode in your browser
                 gatekeeper scan FILE  check a page from the terminal"""
import argparse
import logging
import socket
import threading
import webbrowser


def _free_port(start: int) -> int:
    for port in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit(f"No free port found near {start}. Use --port to pick one.")


def run_learn(port: int = 8765, open_browser: bool = True) -> None:
    from .learn.app import create_app
    port = _free_port(port)
    url = f"http://127.0.0.1:{port}"
    print(f"Gatekeeper Learn Mode is running at {url}\nPress Ctrl+C to stop.")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    create_app().run(host="127.0.0.1", port=port, debug=False)


def run_scan(target: str, no_layer3: bool) -> None:
    from .core import AUTO, safe_fetch
    result = safe_fetch(target, llm=None if no_layer3 else AUTO)
    print(f"decision: {result.decision.upper()}   score: {result.score}")
    for card in result.lessons():
        print(f"\n[{card['points']:+d}] {card['title']}\n    found: {card['evidence']}\n    why:   {card['why']}")
    if result.llm_verdict:
        print(f"\nAI check: {result.llm_verdict['verdict']} ({result.llm_verdict['reason']})")
    if result.note:
        print("\nnote:", result.note)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="gatekeeper", description="Check what your AI agent reads before it acts.")
    sub = p.add_subparsers(dest="cmd")
    learn = sub.add_parser("learn", help="open Learn Mode in your browser (default)")
    learn.add_argument("--port", type=int, default=8765)
    learn.add_argument("--no-browser", action="store_true")
    scan = sub.add_parser("scan", help="check a URL or HTML file")
    scan.add_argument("target")
    scan.add_argument("--no-layer3", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "scan":
        run_scan(args.target, args.no_layer3)
    else:
        run_learn(getattr(args, "port", 8765), not getattr(args, "no_browser", False))


if __name__ == "__main__":
    main()
