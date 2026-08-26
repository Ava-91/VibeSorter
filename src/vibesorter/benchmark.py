from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from .pipeline import analyze_image
from .scanner import find_images


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    images: int
    repeats: int
    elapsed_seconds: float
    images_per_second: float
    milliseconds_per_image: float

    def to_dict(self) -> dict:
        return asdict(self)


def benchmark(folder: str | Path, *, recursive: bool = True, repeats: int = 1) -> BenchmarkResult:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    images = find_images(Path(folder), recursive=recursive)
    started = perf_counter()
    for _ in range(repeats):
        for path in images:
            analyze_image(path)
    elapsed = perf_counter() - started
    total = len(images) * repeats
    return BenchmarkResult(len(images), repeats, elapsed, total / elapsed if elapsed else 0.0, (elapsed / total * 1000) if total else 0.0)
