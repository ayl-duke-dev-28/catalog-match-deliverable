import json
import mimetypes
import os
from functools import lru_cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from catalog_match.data import load_catalog, load_orders
from catalog_match.matcher import CatalogMatcher


BASE_DIR = Path(__file__).resolve().parent


@lru_cache
def matcher() -> CatalogMatcher:
    catalog = load_catalog(BASE_DIR / "catalog.csv")
    orders = load_orders(BASE_DIR / "order-history.csv")
    return CatalogMatcher(catalog, orders)


class CatalogMatchHandler(SimpleHTTPRequestHandler):
    server_version = "CatalogMatch/1.0"

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send_file(BASE_DIR / "static" / "index.html")
            return
        if self.path == "/api/customers":
            self._send_json(matcher().customer_options())
            return
        if self.path == "/api/health":
            current = matcher()
            self._send_json(
                {
                    "status": "ok",
                    "products": len(current.products),
                    "customers": len(current.customers),
                }
            )
            return
        if self.path.startswith("/static/"):
            relative = unquote(self.path.removeprefix("/static/"))
            target = (BASE_DIR / "static" / relative).resolve()
            static_root = (BASE_DIR / "static").resolve()
            if static_root in target.parents and target.is_file():
                self._send_file(target)
                return
        self._send_json({"detail": "Not found."}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path != "/api/match":
            self._send_json({"detail": "Not found."}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self._send_json({"detail": "Invalid JSON."}, HTTPStatus.BAD_REQUEST)
            return

        query = str(payload.get("query", "")).strip()
        if not query:
            self._send_json({"detail": "Description is required."}, HTTPStatus.BAD_REQUEST)
            return
        customer_id = payload.get("customer_id") or None
        self._send_json(matcher().match(query, customer_id=customer_id, limit=3))

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    host = os.getenv("CATALOG_MATCH_HOST", "127.0.0.1")
    port = int(os.getenv("CATALOG_MATCH_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), CatalogMatchHandler)
    print(f"Catalog Match running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Catalog Match.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
