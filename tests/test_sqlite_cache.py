from pathlib import Path

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
