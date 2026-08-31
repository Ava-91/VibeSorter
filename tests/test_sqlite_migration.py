import json
from dataclasses import asdict
from pathlib import Path

from PIL import Image

from vibesorter.cache import AnalysisCache
from vibesorter.features import extract_features
from vibesorter.vibes import score_vibes


def test_legacy_json_is_migrated(tmp_path):
    image = Path(tmp_path) / 'sample.png'; Image.new('RGB', (8, 8), 'navy').save(image)
    features = extract_features(image); scores = score_vibes(features)
    feature_data = asdict(features); feature_data['path'] = str(features.path)
    legacy = Path(tmp_path) / '.vibesorter'; legacy.mkdir()
    payload = {'version': 2, 'entries': {str(image): {'identity': {'size': image.stat().st_size, 'mtime_ns': image.stat().st_mtime_ns}, 'result': {'features': feature_data, 'scores': [asdict(score) for score in scores]}}}}
    (legacy / 'analysis.json').write_text(json.dumps(payload), encoding='utf-8')
    cache = AnalysisCache(legacy / 'analysis.db')
    assert cache.get(image) is not None
