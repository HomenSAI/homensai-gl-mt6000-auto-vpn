"""Static loopback-published demo. No router access or writable HTTP API."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).parent
FILES = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
         "/app.js": ("app.js", "text/javascript"), "/model.js": ("model.js", "text/javascript"),
         "/style.css": ("style.css", "text/css")}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        entry = FILES.get(self.path.split("?", 1)[0])
        if not entry:
            self.send_error(404)
            return
        data = (ROOT / entry[0]).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", entry[1] + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer((os.environ.get("BIND", "127.0.0.1"), int(os.environ.get("PORT", "8798"))), Handler).serve_forever()
