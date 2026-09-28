from __future__ import annotations

from PIL import Image


def install() -> None:
    replacement = getattr(Image.Image, "get_flattened_data", None)
    if replacement is not None:
        Image.Image.getdata = replacement
