from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from ..browser.server import run_server


def run_desktop(db_path: str | Path = ".vibesorter/analysis.db", port: int = 8765) -> None:
    """Compatibility entry point for the pre-Tauri CLI.

    The native desktop application now lives in src-tauri. This command keeps
    the old CLI surface useful by serving the same local browser UI without
    pulling Tkinter into the package.
    """
    url = f"http://127.0.0.1:{port}"
    print("The native VibeSorter desktop app is provided by the Tauri build.")
    print(f"Starting the local browser compatibility mode at {url}")
    webbrowser.open(url)
    run_server(db_path, host="127.0.0.1", port=port)


def main() -> None:
    parser = argparse.ArgumentParser(description="VibeSorter desktop compatibility mode")
    parser.add_argument("--db", default=".vibesorter/analysis.db")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_desktop(args.db, args.port)


if __name__ == "__main__":
    main()
