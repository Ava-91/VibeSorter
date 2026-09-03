from __future__ import annotations

import json
from pathlib import Path

from .scanner import find_images


def sample_image_paths(images: list[Path], count: int) -> list[Path]:
    """Return *count* deterministic, evenly distributed image paths."""
    if count < 1:
        raise ValueError("count must be at least 1")
    if count > len(images):
        raise ValueError(f"count ({count}) exceeds available images ({len(images)})")
    if count == len(images):
        return list(images)
    if count == 1:
        return [images[0]]

    last = len(images) - 1
    return [images[round(index * last / (count - 1))] for index in range(count)]


def write_label_template(paths: list[Path], output: str | Path) -> Path:
    """Write a JSONL human-labeling template and return its output path."""
    destination = Path(output).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for path in paths:
            handle.write(json.dumps({"path": str(path.resolve()), "label": ""}, ensure_ascii=False) + "\n")
    return destination


def sample_labels(
    folder: str | Path,
    *,
    count: int,
    output: str | Path = "labels.jsonl",
    recursive: bool = True,
) -> dict[str, int | str]:
    """Create a deterministic local-only JSONL labeling template."""
    images = find_images(folder, recursive=recursive)
    selected = sample_image_paths(images, count)
    destination = write_label_template(selected, output)
    return {"available": len(images), "selected": len(selected), "output": str(destination)}
