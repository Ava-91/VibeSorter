from vibesorter.pipeline import analyze_image


def test_pipeline_returns_ranked_result(image_factory):
    path = image_factory("sample.png", (80, 120, 180))
    result = analyze_image(path)
    assert result.path == path
    assert result.best.name
    assert result.best.score >= 0
