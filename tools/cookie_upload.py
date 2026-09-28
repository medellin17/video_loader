#!/usr/bin/env python3
"""
One-shot cookie uploader for videoloader.

Serves exactly ONE request on an ephemeral port, requires a 32-byte token in
the path, writes the body to cookies_inst.txt with 0600 perms, then exits.
There is no directory listing, no second request, and the token dies with it.

Usage:
    python3 tools/cookie_upload.py          # prints URL + token, then blocks
    curl -X POST --data-binary @cookies.txt "http://<host>:<port>/<token>"

Kill it any time with Ctrl+C; nothing persists.
"""

import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

TARGET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies_inst.txt")
MAX_BYTES = 512 * 1024
TOKEN = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, body):
        payload = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        # Refuse to confirm existence of a valid path to scanners.
        self._reply(404, "not found\n")

    def do_POST(self):
        if self.path.lstrip("/") != TOKEN:
            self._reply(403, "bad token\n")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._reply(400, "bad content-length\n")
            return

        if length <= 0 or length > MAX_BYTES:
            self._reply(400, "empty or too large\n")
            return

        body = self.rfile.read(length)
        text = body.decode("utf-8", errors="replace")

        # Sanity check: Netscape cookie file must look like one.
        if "# Netscape HTTP Cookie File" not in text or "sessionid" not in text:
            self._reply(
                400,
                "does not look like an Instagram cookie file "
                "(need Netscape header + sessionid)\n",
            )
            return

        # Write atomically so the running bot never sees a half file.
        tmp = TARGET + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, TARGET)

        names = [ln.split("\t")[5] for ln in text.splitlines() if ln.count("\t") >= 6]
        self._reply(200, f"saved {len(names)} cookies: {', '.join(names)}\n")
        print(f"[cookie_upload] saved {len(names)} cookies to {TARGET}", flush=True)
        # Shut down after responding so the socket closes.
        self.server.shutdown_requested = True

    def log_message(self, *a):
        pass


def main():
    server = HTTPServer(("0.0.0.0", 0), Handler)
    port = server.server_address[1]
    host = os.environ.get("PUBLIC_HOST", "144.31.221.127")

    print("=" * 60)
    print("One-shot uploader is live. Run this on YOUR machine:")
    print()
    print(f'  curl -X POST --data-binary @cookies.txt "http://{host}:{port}/{TOKEN}"')
    print()
    print("Waiting for exactly one upload... Ctrl+C to abort.")
    print("=" * 60, flush=True)

    try:
        while not getattr(server, "shutdown_requested", False):
            server.handle_request()
    except KeyboardInterrupt:
        print("\n[cookie_upload] aborted, nothing written")
    finally:
        server.server_close()
        print("[cookie_upload] closed. Port is free again.")


if __name__ == "__main__":
    sys.exit(main())
