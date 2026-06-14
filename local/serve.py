"""
local/serve.py -- minimal dev HTTP server for gh-stats.

Synthesizes an AWS Lambda Function URL v2-style event from each incoming GET
request and delegates to handler.handler(), then writes the response back over
HTTP.  Tokens are read from the environment (PAT_1 or GH_TOKEN) by the
common.secrets module at cold-start -- just export the variable before running.

Usage:
    cd /path/to/gh-stats
    PAT_1=ghp_... python local/serve.py

Then open:
    http://localhost:8000/api?username=YOUR_USERNAME&theme=dark
"""

from __future__ import annotations

import http.server
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler
from typing import Any

# ---------------------------------------------------------------------------
# Ensure src/ is importable (handler imports siblings without "src." prefix).
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")

if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import handler as gh_handler  # noqa: E402 -- must come after sys.path manipulation


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

_HOST = "127.0.0.1"
_PORT = 8000


class _GHStatsHandler(BaseHTTPRequestHandler):
    """Translate HTTP GETs into Lambda v2 events and write SVG responses."""

    def do_GET(self) -> None:  # noqa: N802 -- stdlib method name convention
        parsed = urllib.parse.urlparse(self.path)
        raw_path: str = parsed.path or "/"
        raw_qs: str = parsed.query or ""

        # Build decoded query-string dict (matching Lambda's queryStringParameters).
        qs_params: dict[str, str] = {}
        if raw_qs:
            for key, values in urllib.parse.parse_qs(raw_qs, keep_blank_values=False).items():
                # Lambda collapses repeated keys to the last value; mirror that.
                qs_params[key] = values[-1]

        # Synthesize the Lambda Function URL payload-format-v2 event.
        event: dict[str, Any] = {
            "rawPath": raw_path,
            "rawQueryString": raw_qs,
            "queryStringParameters": qs_params,
        }

        response = gh_handler.handler(event, context=None)

        status_code: int = response.get("statusCode", 200)
        headers: dict[str, str] = response.get("headers", {})
        body: str = response.get("body", "")

        self.send_response(status_code)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()

        self.wfile.write(body.encode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: N802
        # Keep the default stdlib access log but suppress the noisy timestamp prefix.
        sys.stderr.write(f"[serve] {fmt % args}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    server = http.server.HTTPServer((_HOST, _PORT), _GHStatsHandler)
    base_url = f"http://localhost:{_PORT}"
    print(f"gh-stats dev server running at {base_url}")
    print(f"Tokens: set PAT_1 or GH_TOKEN in env before starting.")
    print()
    print(f"  open {base_url}/api?username=YOUR_USERNAME&theme=dark")
    print(f"  open {base_url}/api/top-langs?username=YOUR_USERNAME")
    print(f"  open {base_url}/api/pin?username=YOUR_USERNAME&repo=REPO_NAME")
    print(f"  open {base_url}/api/gist?id=GIST_ID")
    print(f"  open {base_url}/api/wakatime?username=YOUR_WAKATIME_USERNAME")
    print()
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
