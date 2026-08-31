"""Cross-platform desktop shell using only the Python standard library.

The first desktop layer deliberately launches the same local browser instead of
creating a second analysis implementation. A later packaged build can replace
this shell without changing the VibeSorter core.
"""

from __future__ import annotations

import argparse
import threading
import tkinter as tk
import webbrowser
from pathlib import Path

from vibesorter_browser.server import create_app
from http.server import ThreadingHTTPServer


def main() -> None:
    parser = argparse.ArgumentParser(description="VibeSorter desktop application")
    parser.add_argument("--db", default=".vibesorter/analysis.db")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), create_app(Path(args.db)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{args.port}"

    root = tk.Tk()
    root.title("VibeSorter")
    root.geometry("520x300")
    tk.Label(root, text="VibeSorter", font=("Segoe UI", 22, "bold")).pack(pady=(42, 8))
    tk.Label(root, text="Browse your local cached image analysis.").pack(pady=4)
    tk.Label(root, text="Nothing is uploaded. The browser uses the local SQLite index.").pack(pady=4)
    tk.Button(root, text="Open Vibe Browser", command=lambda: webbrowser.open(url)).pack(pady=24)
    tk.Label(root, text=f"Local address: {url}", fg="#777").pack()

    def close() -> None:
        server.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()


if __name__ == "__main__":
    main()
