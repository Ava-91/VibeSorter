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
