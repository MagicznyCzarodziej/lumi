"""Serve library home HTML mockup over HTTP (TMDB posters need http, not file://)."""

from __future__ import annotations

import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import time

_PORT = 8765
_DIR = Path(__file__).resolve().parent


class _MockupHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def main() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", _PORT), _MockupHandler)
    v = int(time())
    base = f"http://127.0.0.1:{_PORT}"
    url = f"{base}/library-home.html?v={v}"
    print(f"Serving {_DIR} at {url}")
    print(f"  Series: {base}/series-open.html?v={v}")
    print("  ?series=kusuriya|shingeki|severance|kaguya")
    print("Ctrl+C to stop.")

    if sys.platform == "darwin":
        subprocess.Popen(["open", url], start_new_session=True)
    elif sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", "start", "", url], start_new_session=True)
    else:
        subprocess.Popen(["xdg-open", url], start_new_session=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
