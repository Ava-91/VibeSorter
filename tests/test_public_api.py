from __future__ import annotations

import vibesorter


def test_public_api_exports_are_importable():
    exported = set(vibesorter.__all__)
    assert exported
    assert exported == {name for name in exported if hasattr(vibesorter, name)}
    assert len(exported) == len(vibesorter.__all__)


def test_core_models_are_public():
    assert vibesorter.AnalysisCache is not None
    assert vibesorter.ImageProfile is not None
    assert vibesorter.analyze_image is not None
    assert vibesorter.classify_profile is not None
