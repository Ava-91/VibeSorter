from __future__ import annotations

import argparse
from pathlib import Path

from .scanner import find_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibesorter",
        description="Organize images locally by their visual vibe.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover supported images in a folder.")
    scan.add_argument("folder", type=Path, help="Folder to scan.")
    scan.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only scan the selected folder, not its subfolders.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        try:
            images = find_images(args.folder, recursive=not args.no_recursive)
        except (FileNotFoundError, NotADirectoryError) as exc:
            parser.error(str(exc))

        print(f"Found {len(images)} image(s) in {args.folder.expanduser()}")
        for image in images:
            print(image)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
