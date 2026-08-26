from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmark import benchmark
from .explain import explain_image
from .cli import main as legacy_main


_NEW_COMMANDS = {"benchmark", "explain"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibesorter",
        description="Detect visual vibes in local images and safely organize large image libraries.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("benchmark", help="Measure classifier performance without modifying files.")
    command.add_argument("folder", type=Path, help="Folder containing images to benchmark.")
    command.add_argument("--no-recursive", action="store_true", help="Only benchmark the selected folder.")
    command.add_argument("--repeats", type=int, default=1, help="Number of benchmark passes (default: 1).")
    command.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    command = subparsers.add_parser("explain", help="Explain how an image received its vibe prediction.")
    command.add_argument("image", type=Path, help="Image file to explain.")
    command.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def _run_benchmark(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    try:
        result = benchmark(args.folder.expanduser(), recursive=not args.no_recursive, repeats=args.repeats)
    except (FileNotFoundError, NotADirectoryError, ValueError, OSError) as exc:
        parser.error(str(exc))
    data = result.to_dict()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("=== VibeSorter benchmark ===")
        print(f"Images: {data['images']}")
        print(f"Repeats: {data['repeats']}")
        print(f"Elapsed: {data['elapsed_seconds']:.4f}s")
        print(f"Throughput: {data['images_per_second']:.2f} images/s")
        print(f"Average: {data['milliseconds_per_image']:.2f} ms/image")
        print("\nBenchmark is read-only; no files were modified.")
    return 0


def _run_explain(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        explanation = explain_image(args.image.expanduser())
    except (FileNotFoundError, OSError, ValueError) as exc:
        parser.error(str(exc))
    data = explanation.to_dict()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    print(f"Image: {data['path']}")
    print(f"Winner: {data['winner']}")
    print(f"Confidence: {data['confidence']:.0%}")
    print(f"Margin: {data['margin']:.4f}")
    print(f"Ambiguous: {'yes' if data['ambiguous'] else 'no'}")
    print("\nRanked vibes:")
    for name, score in data["scores"]:
        print(f"  {name:<18} {score:.0%}")
    print("\nExtracted features:")
    for name, value in data["features"].items():
        print(f"  {name}: {value}")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] in _NEW_COMMANDS:
        parser = _parser()
        args = parser.parse_args(argv)
        if args.command == "benchmark":
            return _run_benchmark(args, parser)
        return _run_explain(args, parser)
    if argv and argv[0] in {"--help", "-h"}:
        legacy_main()
        print("\nAdditional commands:")
        print("  benchmark FOLDER  Measure classifier performance without modifying files.")
        print("  explain IMAGE     Explain the prediction, confidence, scores, and features.")
        return 0
    return legacy_main()
