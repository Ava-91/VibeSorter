from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import analyze_image
from .scanner import find_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibesorter",
        description="Organize images locally by their visual vibe.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover supported images in a folder.")
    scan.add_argument("folder", type=Path, help="Folder to scan.")
    scan.add_argument("--no-recursive", action="store_true", help="Only scan the selected folder.")

    analyze = subparsers.add_parser("analyze", help="Analyze images locally and print their vibe rankings.")
    analyze.add_argument("folder", type=Path, help="Folder containing images.")
    analyze.add_argument("--no-recursive", action="store_true", help="Only analyze the selected folder.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        images = find_images(args.folder, recursive=not args.no_recursive)
    except (FileNotFoundError, NotADirectoryError) as exc:
        parser.error(str(exc))

    if args.command == "scan":
        print(f"Found {len(images)} image(s) in {args.folder.expanduser()}")
        for image in images:
            print(image)
        return 0

    print(f"Analyzing {len(images)} image(s) locally in {args.folder.expanduser()}\n")
    successful = 0
    failed = 0

    for path in images:
        try:
            result = analyze_image(path)
        except Exception as exc:
            failed += 1
            print(f"[SKIP] {path}: {exc}")
            continue

        successful += 1
        print(f"[OK]   {path}")
        for rank, score in enumerate(result.scores[:3], start=1):
            print(f"       {rank}. {score.name}: {score.score:.0%}")
        print()

    print(f"Done — {successful} analyzed, {failed} skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
