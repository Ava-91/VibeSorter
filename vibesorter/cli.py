from __future__ import annotations

import argparse
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .pipeline import analyze_image
from .scanner import find_images
from .vibes import REVIEW_VIBE, is_confident


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vibesorter", description="Organize images locally by their visual vibe.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (("scan", "Discover supported images."), ("preview", "Analyze and preview vibe groups without changing files.")):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("folder", type=Path, help="Folder to scan or analyze.")
        command.add_argument("--no-recursive", action="store_true", help="Only use the selected folder.")
        if name == "preview":
            default_workers = min(8, max(1, os.cpu_count() or 1))
            command.add_argument(
                "--workers",
                type=int,
                default=default_workers,
                help=f"Number of images to analyze concurrently (default: {default_workers}).",
            )

    return parser


def _analyze_one(path: Path):
    try:
        return analyze_image(path), None
    except Exception as exc:
        return None, exc


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

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    groups: dict[str, list[tuple[Path, float, float]]] = defaultdict(list)
    skipped = 0
    needs_review = 0
    print(
        f"Previewing {len(images)} image(s) locally in {args.folder.expanduser()} "
        f"using {args.workers} worker(s)\n"
    )

    # Image decoding and Pillow's native operations can run concurrently, so
    # large libraries spend less time waiting for one image at a time.
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for index, (result, error) in enumerate(executor.map(_analyze_one, images), start=1):
            path = images[index - 1]
            if error is not None:
                skipped += 1
                print(f"[{index}/{len(images)}] SKIP  {path}: {error}")
                continue

            runner_up = result.scores[1].score if len(result.scores) > 1 else 0.0
            margin = result.best.score - runner_up
            if not is_confident(result.scores):
                needs_review += 1
                groups[REVIEW_VIBE].append((path, result.best.score, margin))
                print(
                    f"[{index}/{len(images)}] {REVIEW_VIBE:<18} "
                    f"{result.best.score:>5.0%} (gap {margin:>4.0%})  {path}"
                )
                continue

            groups[result.best.name].append((path, result.best.score, margin))
            print(
                f"[{index}/{len(images)}] {result.best.name:<18} "
                f"{result.best.score:>5.0%} (gap {margin:>4.0%})  {path}"
            )

    print("\n=== Proposed vibe folders ===")
    for vibe, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f"\n{vibe} — {len(items)} image(s)")
        for path, score, margin in items[:5]:
            print(f"  {score:>5.0%} (gap {margin:>4.0%})  {path}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    print(f"\nPreview complete — {len(images) - skipped} analyzed, {skipped} skipped.")
    print(f"Needs review — {needs_review} ambiguous image(s).")
    print("No files were created, moved, copied, or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
