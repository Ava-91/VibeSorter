from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def image_factory(tmp_path: Path):
    def create(name: str, color=(128, 128, 128), size=(32, 32)) -> Path:
        path = tmp_path / name
        Image.new("RGB", size, color).save(path)
        return path
    return create
