from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from .pipeline import analyze_image
from .scanner import find_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vibesorter", description="Organize images locally by their visual vibe.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (("scan", "Discover supported images."), ("preview", "Analyze and preview vibe groups without changing files.")):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("folder", type=Path, help="Folder to scan or analyze.")
        command.add_argument("--no-recursive", action="store_true", help="Only use the selected folder.")

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

    groups: dict[str, list[tuple[Path, float]]] = defaultdict(list)
    skipped = 0
    print(f"Previewing {len(images)} image(s) locally in {args.folder.expanduser()}\n")

    for index, path in enumerate(images, start=1):
        try:
            result = analyze_image(path)
        except Exception as exc:
            skipped += 1
            print(f"[{index}/{len(images)}] SKIP  {path}: {exc}")
            continue
        groups[result.best.name].append((path, result.best.score))
        print(f"[{index}/{len(images)}] {result.best.name:<18} {result.best.score:>5.0%}  {path}")

    print("\n=== Proposed vibe folders ===")
    for vibe, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f"\n{vibe} — {len(items)} image(s)")
        for path, score in items[:5]:
            print(f"  {score:>5.0%}  {path}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    print(f"\nPreview complete — {len(images) - skipped} analyzed, {skipped} skipped.")
    print("No files were created, moved, copied, or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
