"""Record/replay a mock upstream for controllable-network inputs (e.g. `gron <url>`).

So URL-input behaviour is deterministic for golden capture AND grading:
  record(urls) -> fetch each once, freeze {path: {status, body_b64}} to a fixtures file.
  start_replay(fixtures) -> a local http.server that serves the frozen responses;
                            point the SUT at its base_url; returns (base_url, stop()).

The original (ref) and every candidate hit the SAME frozen upstream, never the live net.
"""
from __future__ import annotations

import base64
import http.server
import json
import threading
import urllib.request


def record(urls: list[str], timeout=20) -> dict:
    fixtures = {}
    for u in urls:
        path = urllib.parse_path(u) if hasattr(urllib, "parse_path") else _path(u)
        with urllib.request.urlopen(u, timeout=timeout) as r:
            body = r.read()
            fixtures[path] = {"status": r.status, "body_b64": base64.b64encode(body).decode()}
    return fixtures


def _path(url: str) -> str:
    from urllib.parse import urlsplit
    s = urlsplit(url)
    return s.path + (("?" + s.query) if s.query else "")


def start_replay(fixtures: dict, host="127.0.0.1", port=0):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            rec = fixtures.get(self.path)
            if rec is None:
                self.send_response(404); self.end_headers(); return
            body = base64.b64decode(rec["body_b64"])
            self.send_response(rec.get("status", 200))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # quiet
            pass

    srv = http.server.HTTPServer((host, port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://{host}:{srv.server_address[1]}"
    return base, srv.shutdown


def load(path):
    return json.loads(open(path, encoding="utf-8").read())
