"""CareerBuddy — Flask navigation server.

Serves index.html as the home page and every lesson file in this project
under its existing path. No SPA-fallback routing: missing files return a
real, themed 404. Designed to make the iframe-based in-page viewer load
every lesson cleanly, including same-filename `index.html` files in
subdirectories (the failure mode that broke VS Code Live Preview).

Run with:
    python app.py                  # default: 127.0.0.1:5000
    python app.py --port 8000      # custom port
    python -m flask --app app run  # via flask CLI
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
from html import escape
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"

# Don't surface internal/dev files through the file route.
HIDDEN_PREFIXES = {".git", ".claude", ".vscode", "__pycache__", "memory"}
HIDDEN_SUFFIXES = {".py", ".pyc", ".bat", ".ps1", ".log"}

# Make sure browsers pick the right MIME for the file types we serve.
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=None)
app.config["JSON_SORT_KEYS"] = False


def _safe_resolve(relpath: str) -> Path | None:
    """Resolve `relpath` under ROOT, returning None if it escapes or is hidden."""
    if not relpath:
        return None
    try:
        candidate = (ROOT / relpath).resolve()
    except (OSError, ValueError):
        return None
    # Prevent directory traversal: candidate must live under ROOT.
    try:
        rel = candidate.relative_to(ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    if parts[0] in HIDDEN_PREFIXES:
        return None
    if candidate.suffix.lower() in HIDDEN_SUFFIXES:
        return None
    return candidate


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Serve the unified hub."""
    return send_from_directory(ROOT, "index.html")


@app.route("/healthz")
def healthz():
    return jsonify(status="ok", root=str(ROOT), index_exists=INDEX.is_file())


@app.route("/api/sitemap")
def api_sitemap():
    """Return the navigable sitemap as JSON, derived from index.html.

    Useful for verifying every level-3 link still resolves, and for any
    future client that wants to render the sitemap without parsing HTML.
    """
    html = INDEX.read_text(encoding="utf-8", errors="ignore")
    # All level-3 deep links live in href="#load=<path>&title=<title>"
    rx = re.compile(r'href="#load=([^&"]+)(?:&title=([^"]+))?"')
    seen: dict[str, str] = {}
    for m in rx.finditer(html):
        path = m.group(1)
        title = m.group(2) or path
        # Keep the FIRST title we see for any given path.
        seen.setdefault(path, title)
    entries = [{"path": p, "title": t} for p, t in seen.items()]
    return jsonify(count=len(entries), entries=entries)


@app.route("/<path:filename>")
def file(filename: str):
    """Serve any file under the project root, including deeply nested ones.

    Flask URL-decodes `filename` automatically, so '%20' arrives as ' '.
    `send_from_directory` re-encodes safely when generating responses.
    """
    target = _safe_resolve(filename)
    if target is None or not target.exists():
        abort(404)
    # If the resolved path is a directory, serve its index.html (if any).
    if target.is_dir():
        idx = target / "index.html"
        if idx.is_file():
            return send_from_directory(target, "index.html")
        abort(404)
    if not target.is_file():
        abort(404)
    rel = target.relative_to(ROOT).as_posix()
    return send_from_directory(ROOT, rel)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
_ERROR_TEMPLATE = """\
<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{code} — CareerBuddy</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;font:15px/1.55 'Manrope',system-ui,sans-serif;color:#161c27;background:#f9f9ff;
       min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px}}
  .card{{max-width:520px;background:#fff;border:1px solid #e2e8f0;border-radius:14px;
       padding:32px;box-shadow:0 8px 24px -12px rgba(16,24,40,.18)}}
  .badge{{display:inline-grid;place-items:center;width:44px;height:44px;border-radius:10px;
       background:#fdf3d3;color:#7a5c00;font-weight:800;font-size:20px;margin-bottom:14px}}
  h1{{margin:0 0 8px;font-size:22px;color:#00352e;letter-spacing:-.01em}}
  p{{margin:8px 0;color:#4a5568}}
  code{{background:#f1f3ff;padding:3px 8px;border-radius:4px;
       font:12.5px 'JetBrains Mono',ui-monospace,monospace;color:#0a4d44;word-break:break-all}}
  .btns{{margin-top:20px;display:flex;gap:10px;flex-wrap:wrap}}
  a.btn{{display:inline-flex;align-items:center;gap:6px;padding:10px 18px;border-radius:8px;
       text-decoration:none;font-weight:600;font-size:14px;border:1px solid transparent}}
  a.primary{{background:#00352e;color:#fff}}
  a.secondary{{background:#fff;color:#0a4d44;border-color:#e2e8f0}}
</style></head><body><div class="card">
  <div class="badge">{code}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <p>Requested: <code>{path}</code></p>
  <div class="btns">
    <a class="btn primary" href="/">Back to hub</a>
    <a class="btn secondary" href="/api/sitemap">View sitemap JSON</a>
  </div>
</div></body></html>"""


@app.errorhandler(404)
def not_found(err):
    body = _ERROR_TEMPLATE.format(
        code=404,
        title="Page not found",
        message="No lesson lives at this path. Use the sitemap to find what you’re looking for.",
        path=escape(request.path),
    )
    return body, 404


@app.errorhandler(403)
def forbidden(err):
    body = _ERROR_TEMPLATE.format(
        code=403,
        title="Forbidden",
        message="That path is not accessible.",
        path=escape(request.path),
    )
    return body, 403


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="bind port (default 5000)")
    parser.add_argument("--debug", action="store_true", help="enable Flask debug")
    args = parser.parse_args(argv)

    if not INDEX.is_file():
        print(f"!! index.html not found in {ROOT}", file=sys.stderr)
        return 1

    url = f"http://{args.host}:{args.port}/"
    print()
    print(" =====================================================")
    print("  CareerBuddy (Flask) is serving at:")
    print(f"  {url}")
    print(" =====================================================")
    print("  index.html is served as the home page.")
    print("  Press Ctrl+C to stop.")
    print()
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
