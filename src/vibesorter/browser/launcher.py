from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path

from .server import run_server


def _is_loopback(host: str) -> bool:
    value = host.strip().lower()
    if value == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vibesorter-browser",
        description="Browse a local VibeSorter analysis cache.",
    )
    parser.add_argument("--db", type=Path, default=Path(".vibesorter/analysis.db"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow binding to a non-loopback host and exposing cached images to the network.",
    )
    args = parser.parse_args()
    if not args.allow_network and not _is_loopback(args.host):
        parser.error("non-loopback browser hosts require --allow-network")
    run_server(args.db, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
