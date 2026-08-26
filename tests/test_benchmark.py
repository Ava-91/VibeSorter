import pytest

from vibesorter.benchmark import benchmark


def test_benchmark_reports_timing(image_factory, tmp_path):
    image_factory("one.png", (20, 30, 40))
    result = benchmark(tmp_path)
    assert result.images == 1
    assert result.repeats == 1
    assert result.elapsed_seconds >= 0
    assert result.milliseconds_per_image >= 0


def test_benchmark_rejects_zero_repeats(tmp_path):
    with pytest.raises(ValueError):
        benchmark(tmp_path, repeats=0)
