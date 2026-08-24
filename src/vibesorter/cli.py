from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .pipeline import analyze_image
from .scanner import find_images
from .vibes import VIBES, confidence_score


def _add_folder_argument(command: argparse.ArgumentParser) -> None:
    command.add_argument("folder", type=Path, help="Folder to scan or analyze.")
    command.add_argument("--no-recursive", action="store_true", help="Only use the selected folder.")


def _add_workers_argument(command: argparse.ArgumentParser) -> None:
    default_workers = min(8, max(1, os.cpu_count() or 1))
    command.add_argument("--workers", type=int, default=default_workers,
                         help=f"Number of images to analyze concurrently (default: {default_workers}).")


def _add_filter_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--vibe", choices=VIBES, help="Only include images whose best vibe matches this category.")
    command.add_argument("--min-score", type=float, default=0.0,
                         help="Ignore classifications below this confidence from 0 to 1 (default: 0).")
    command.add_argument("--max-text-likelihood", type=float, default=1.0,
                         help="Skip images whose text/screenshot likelihood exceeds this value (default: 1).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibesorter",
        description="Detect visual vibes in local images without changing the files.",
        epilog="Examples: vibesorter scan ./photos | vibesorter preview ./photos | vibesorter analyze ./photo.jpg | vibesorter stats ./photos",
    )
    parser.add_argument("--version", action="version", version="VibeSorter 0.3.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover supported images (read-only).")
    _add_folder_argument(scan)

    preview = subparsers.add_parser("preview", help="Detect vibes for a folder without changing files.")
    _add_folder_argument(preview)
    _add_workers_argument(preview)
    _add_filter_arguments(preview)
    preview.add_argument("--top", type=int, default=5, help="Number of example paths shown per vibe (default: 5).")
    preview.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of the text report.")

    analyze = subparsers.add_parser("analyze", help="Detect the vibe of one image and show its ranking.")
    analyze.add_argument("image", type=Path, help="Image file to analyze.")
    analyze.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    stats = subparsers.add_parser("stats", help="Summarize vibe counts for a folder.")
    _add_folder_argument(stats)
    _add_workers_argument(stats)
    _add_filter_arguments(stats)
    stats.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of the text report.")

    return parser


def _analyze_one(path: Path):
    try:
        return analyze_image(path), None
    except Exception as exc:
        return None, exc


def _analyze_many(images: list[Path], workers: int):
    if workers < 1:
        raise ValueError("--workers must be at least 1")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        yield from executor.map(_analyze_one, images)


def _load_images(args, parser: argparse.ArgumentParser) -> list[Path]:
    try:
        return find_images(args.folder, recursive=not args.no_recursive)
    except (FileNotFoundError, NotADirectoryError) as exc:
        parser.error(str(exc))


def _validate_filters(args, parser: argparse.ArgumentParser) -> None:
    if hasattr(args, "workers") and args.workers < 1:
        parser.error("--workers must be at least 1")
    if hasattr(args, "min_score") and not 0 <= args.min_score <= 1:
        parser.error("--min-score must be between 0 and 1")
    if hasattr(args, "max_text_likelihood") and not 0 <= args.max_text_likelihood <= 1:
        parser.error("--max-text-likelihood must be between 0 and 1")
    if getattr(args, "top", 1) < 1:
        parser.error("--top must be at least 1")


def _analyze_folder(images: list[Path], workers: int, *, vibe: str | None = None,
                    min_score: float = 0.0, max_text_likelihood: float = 1.0,
                    show_progress: bool = True):
    groups: dict[str, list[tuple[Path, float, float]]] = defaultdict(list)
    skipped = 0
    for index, (result, error) in enumerate(_analyze_many(images, workers), start=1):
        path = images[index - 1]
        if error is not None:
            skipped += 1
            if show_progress:
                print(f"[{index}/{len(images)}] SKIP  {path}: {error}")
            continue
        text_likelihood = result.features.text_likelihood
        if text_likelihood > max_text_likelihood:
            continue
        best = result.best
        if best.score < min_score or (vibe is not None and best.name != vibe):
            continue
        groups[best.name].append((path, best.score, text_likelihood))
        if show_progress:
            print(f"[{index}/{len(images)}] {best.name:<18} {best.score:>5.0%}  {path}")
    return groups, skipped


def _json_groups(groups: dict[str, list[tuple[Path, float, float]]], top: int | None = None):
    result = {}
    for vibe_name, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        selected = items if top is None else items[:top]
        result[vibe_name] = {
            "count": len(items),
            "examples": [
                {"path": str(path), "score": round(score, 4), "text_likelihood": round(text, 4)}
                for path, score, text in selected
            ],
            "average_score": round(sum(score for _, score, _ in items) / len(items), 4),
        }
    return result


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        result, error = _analyze_one(args.image.expanduser())
        if error is not None:
            parser.error(str(error))
        if args.json:
            print(json.dumps({
                "path": str(result.path),
                "best": {"name": result.best.name, "score": result.best.score},
                "confidence": confidence_score(result.scores),
                "text_likelihood": result.features.text_likelihood,
                "ranking": [{"name": score.name, "score": score.score} for score in result.scores],
            }, indent=2))
            return 0
        print(f"Image: {result.path}")
        print(f"Best vibe: {result.best.name} ({result.best.score:.0%})")
        print(f"Confidence: {confidence_score(result.scores):.0%}")
        print(f"Text/screenshot likelihood: {result.features.text_likelihood:.0%}\n")
        print("Vibe ranking:")
        for score in result.scores:
            print(f"  {score.name:<18} {score.score:.0%}")
        return 0

    images = _load_images(args, parser)
    if args.command == "scan":
        print(f"Found {len(images)} image(s) in {args.folder.expanduser()}")
        for image in images:
            print(image)
        return 0

    _validate_filters(args, parser)

    if args.command == "stats":
        groups, skipped = _analyze_folder(images, args.workers, vibe=args.vibe,
                                          min_score=args.min_score,
                                          max_text_likelihood=args.max_text_likelihood,
                                          show_progress=False)
        analyzed = len(images) - skipped
        if args.json:
            print(json.dumps({"total": len(images), "analyzed": analyzed, "skipped": skipped,
                              "vibes": _json_groups(groups)}, indent=2))
            return 0
        print(f"Analyzing {len(images)} image(s) for vibe statistics...\n")
        print("=== Vibe statistics ===")
        for vibe_name, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
            average = sum(score for _, score, _ in items) / len(items)
            print(f"{vibe_name:<18} {len(items):>5} image(s)  avg confidence {average:.0%}")
        print(f"\nTotal: {analyzed} analyzed, {skipped} skipped.")
        return 0

    groups, skipped = _analyze_folder(images, args.workers, vibe=args.vibe,
                                      min_score=args.min_score,
                                      max_text_likelihood=args.max_text_likelihood,
                                      show_progress=not args.json)
    if args.json:
        print(json.dumps({"total": len(images), "analyzed": len(images) - skipped, "skipped": skipped,
                          "vibes": _json_groups(groups, args.top)}, indent=2))
        return 0

    print(f"Analyzing {len(images)} image(s) locally in {args.folder.expanduser()}\n")
    print("\n=== Proposed vibe folders ===")
    for vibe_name, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f"\n{vibe_name} — {len(items)} image(s)")
        for path, score, _ in items[:args.top]:
            print(f"  {score:>5.0%}  {path}")
        if len(items) > args.top:
            print(f"  ... and {len(items) - args.top} more")

    print(f"\nAnalysis complete — {len(images) - skipped} analyzed, {skipped} skipped.")
    print("No files were created, moved, copied, or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
