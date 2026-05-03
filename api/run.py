import asyncio
import json
from http.server import BaseHTTPRequestHandler

from vss.pipeline import run


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        result = asyncio.run(run(body.get("query", ""), body.get("provider"), body.get("model")))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(result.model_dump_json().encode())
