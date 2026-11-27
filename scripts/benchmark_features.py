from __future__ import annotations

import argparse
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path

from PIL import Image, ImageDraw

from vibesorter.features import extract_features


def make_fixture(path: Path, size: int) -> None:
    image = Image.new("RGB", (size, size), (126, 126, 126))
    draw = ImageDraw.Draw(image)
    step = max(8, size // 32)
    for x in range(0, size, step):
        color = ((x * 3) % 256, (x * 7) % 256, (x * 11) % 256)
        draw.rectangle((x, 0, min(size, x + step // 2), size), fill=color)
    image.save(path)


def measure(path: Path, repeats: int) -> dict[str, float]:
    durations = []
    tracemalloc.start()
    for _ in range(repeats):
        started = time.perf_counter()
        extract_features(path)
        durations.append(time.perf_counter() - started)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    median = statistics.median(durations)
    ordered = sorted(durations)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return {
        "median_ms": round(median * 1000, 3),
        "p95_ms": round(p95 * 1000, 3),
        "images_per_second": round(1 / median, 2) if median else 0.0,
        "python_peak_kib": round(peak / 1024, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark bounded image feature extraction.")
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    with tempfile.TemporaryDirectory(prefix="vibesorter-feature-bench-") as directory:
        root = Path(directory)
        for size in (256, 1024, 4096):
            path = root / f"fixture-{size}.png"
            make_fixture(path, size)
            print(f"{size}x{size}: {measure(path, args.repeats)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
