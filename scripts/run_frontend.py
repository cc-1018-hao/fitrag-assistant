from __future__ import annotations

import http.server
import socketserver
from pathlib import Path

PORT = 5500
ROOT = Path(__file__).resolve().parents[1] / "frontend"


def main() -> None:
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        print(f"Serving frontend at http://127.0.0.1:{PORT}")
        print(f"Root: {ROOT}")
        import os

        os.chdir(ROOT)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
