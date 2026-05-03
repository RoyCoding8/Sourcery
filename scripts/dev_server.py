from __future__ import annotations

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from vss.pipeline import run
from vss.settings import PROVIDERS, has_creds, models_for

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: object) -> bool:
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write((data if isinstance(data, str) else json.dumps(data)).encode())
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return False
        return True

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/providers":
            self._json(200, [{"name": p, "models": models_for(p), "available": has_creds(p)} for p in PROVIDERS])
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") == "/api/run":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                result = asyncio.run(run(body.get("query", ""), body.get("provider"), body.get("model")))
            except Exception as e:
                self._json(500, {"error": str(e)})
                return
            self._json(200, result.model_dump_json())
            return
        self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[api] {fmt % args}")


if __name__ == "__main__":
    print(f"sourcery dev API -> http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
