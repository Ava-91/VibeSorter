from vibesorter.benchmark import BenchmarkResult


def test_benchmark_result_is_machine_readable():
    result = BenchmarkResult(2, 3, 1.5, 4.0, 250.0)
    assert result.to_dict() == {
        "images": 2, "repeats": 3, "elapsed_seconds": 1.5,
        "images_per_second": 4.0, "milliseconds_per_image": 250.0,
    }
