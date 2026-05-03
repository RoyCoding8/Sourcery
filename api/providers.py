import json
from http.server import BaseHTTPRequestHandler

from vss.settings import PROVIDERS, has_creds, models_for


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps([{"name": p, "models": models_for(p), "available": has_creds(p)} for p in PROVIDERS])
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())
