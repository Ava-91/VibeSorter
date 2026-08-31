import json
from pathlib import Path

from PIL import Image

from vibesorter.cache import AnalysisCache
from vibesorter.features import extract_features
from vibesorter.vibes import score_vibes


def test_legacy_json_is_migrated(tmp_path, monkeypatch):
    image = Path(tmp_path) / 'sample.png'; Image.new('RGB', (8, 8), 'navy').save(image)
    features = extract_features(image); scores = score_vibes(features)
    legacy = Path(tmp_path) / '.vibesorter'; legacy.mkdir()
    (legacy / 'analysis.json').write_text(json.dumps({'version': 2, 'entries': {str(image): {'identity': {'size': image.stat().st_size, 'mtime_ns': image.stat().st_mtime_ns}, 'result': {'features': {**__import__('dataclasses').asdict(features), 'path': str(image)}, 'scores': [__import__('dataclasses').asdict(score) for score in scores]}}}}), encoding='utf-8')
    cache = AnalysisCache(legacy / 'analysis.db')
    assert cache.get(image) is not None
