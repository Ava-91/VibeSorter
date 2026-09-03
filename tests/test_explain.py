import json
from pathlib import Path

from PIL import Image

from vibesorter.explain import explain_image


def test_explain_includes_selected_vibes_and_signals(tmp_path):
    path = Path(tmp_path) / 'sample.png'
    Image.new('RGB', (32, 32), (20, 30, 70)).save(path)
    explanation = explain_image(path)
    assert explanation.winner
    assert explanation.selected_vibes
    assert 'brightness' in explanation.feature_signals
    assert 'center_brightness_delta' in explanation.feature_signals
    assert explanation.to_dict()['path'] == str(path)


def test_explain_json_is_serializable_with_nested_feature_path(tmp_path):
    path = Path(tmp_path) / 'sample.png'
    Image.new('RGB', (32, 32), (20, 30, 70)).save(path)
    data = explain_image(path).to_dict()
    encoded = json.dumps(data, ensure_ascii=False)
    assert str(path) in encoded
    assert data['features']['path'] == str(path)


def test_explain_includes_weighted_score_contributions(tmp_path):
    path = Path(tmp_path) / 'sample.png'
    Image.new('RGB', (32, 32), (20, 30, 70)).save(path)
    data = explain_image(path).to_dict()
    assert set(data['score_contributions']) == {name for name, _ in data['scores']}
    for name, contributions in data['score_contributions'].items():
        assert contributions
        assert all(isinstance(value, (int, float)) for value in contributions.values())
        assert abs(sum(contributions.values()) - dict(data['scores'])[name]) < 0.001
