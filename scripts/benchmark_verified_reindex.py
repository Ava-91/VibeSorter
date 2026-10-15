from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

from vibesorter.indexer import index_folder
from vibesorter.scanner import find_images
from vibesorter.verified_cache import VerifiedAnalysisCache


def _make_dataset(root: Path, count: int, size: int) -> None:
    for index in range(count):
        image = Image.new("RGB", (size, size), ((index * 29) % 256, (index * 47) % 256, (index * 71) % 256))
        draw = ImageDraw.Draw(image)
        draw.rectangle((size // 4, size // 4, size * 3 // 4, size * 3 // 4), fill=((index * 13) % 256, 30, 180))
        image.save(root / f"photo-{index:06}.jpg", quality=88, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark first and repeat VibeSorter indexing on a reproducible synthetic image set.")
    parser.add_argument("--files", type=int, default=250, help="Number of synthetic images (default: 250).")
    parser.add_argument("--size", type=int, default=256, help="Image width and height in pixels (default: 256).")
    parser.add_argument("--workers", type=int, default=4, help="Analysis worker count (default: 4).")
    args = parser.parse_args()
    if args.files < 1 or args.size < 16 or args.workers < 1:
        parser.error("--files and --workers must be positive; --size must be at least 16")

    with tempfile.TemporaryDirectory(prefix="vibesorter-reindex-bench-") as directory:
        root = Path(directory) / "photos"
        root.mkdir()
        _make_dataset(root, args.files, args.size)

        started = time.perf_counter()
        images = find_images(root)
        scan_seconds = time.perf_counter() - started

        started = time.perf_counter()
        first = index_folder(root, workers=args.workers)
        first_seconds = time.perf_counter() - started

        started = time.perf_counter()
        with VerifiedAnalysisCache(root / ".vibesorter" / "analysis.db") as cache:
            verified = cache.get_verified_many(images)
        verify_seconds = time.perf_counter() - started

        started = time.perf_counter()
        repeat = index_folder(root, workers=args.workers)
        repeat_seconds = time.perf_counter() - started

        print(f"dataset: {len(images)} images at {args.size}x{args.size}")
        print(f"scan-only: {scan_seconds:.3f}s")
        print(f"first-index: {first_seconds:.3f}s analyzed={first['analyzed']} reused={first['reused']}")
        print(f"verified-cache-only: {verify_seconds:.3f}s verified={len(verified)}")
        print(f"repeat-index: {repeat_seconds:.3f}s analyzed={repeat['analyzed']} reused={repeat['reused']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
