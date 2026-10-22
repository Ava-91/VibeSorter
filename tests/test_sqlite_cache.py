from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from PIL import Image

from vibesorter.cache import AnalysisCache
from vibesorter.features import extract_features
from vibesorter.vibes import score_vibes


def test_sqlite_cache_round_trip(tmp_path):
    image = Path(tmp_path) / 'sample.png'
    Image.new('RGB', (16, 16), (20, 30, 80)).save(image)
    cache = AnalysisCache(Path(tmp_path) / '.vibesorter' / 'analysis.db')
    features = extract_features(image)
    scores = score_vibes(features)
    cache.set(image, features, scores)
    cache.save()
    loaded = cache.get(image)
    cache.close()
    assert loaded is not None
    assert loaded[1][0] == scores[0]


def test_sqlite_cache_invalidates_changed_image(tmp_path):
    image = Path(tmp_path) / 'sample.png'
    Image.new('RGB', (16, 16), 'black').save(image)
    cache = AnalysisCache(Path(tmp_path) / '.vibesorter' / 'analysis.db')
    features = extract_features(image); cache.set(image, features, score_vibes(features)); cache.save()
    Image.new('RGB', (16, 16), 'white').save(image)
    assert cache.get(image) is None



def test_concurrent_sqlite_cache_writers_preserve_all_entries(tmp_path):
    database = tmp_path / ".vibesorter" / "analysis.db"
    images = []
    for index in range(4):
        image = tmp_path / f"sample-{index}.png"
        Image.new("RGB", (16, 16), (index * 40, 30, 80)).save(image)
        images.append(image)

    # Create the schema before concurrent writers begin.
    AnalysisCache(database).close()
    barrier = Barrier(len(images))

    def write_one(image: Path) -> None:
        with AnalysisCache(database) as cache:
            features = extract_features(image)
            scores = score_vibes(features)
            barrier.wait(timeout=10)
            cache.set(image, features, scores)
            cache.save()

    with ThreadPoolExecutor(max_workers=len(images)) as pool:
        list(pool.map(write_one, images))

    with AnalysisCache(database) as cache:
        assert {path for path, _, _ in cache.entries()} == set(images)
