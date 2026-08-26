from __future__ import annotations

from vibesorter.evaluation import ConfidenceCalibrator, ConfidenceObservation


def test_calibrator_maps_confidence_to_observed_accuracy() -> None:
    observations = (
        ConfidenceObservation("Red / Warm", "Red / Warm", 0.22, True),
        ConfidenceObservation("Red / Warm", "Blue", 0.28, False),
        ConfidenceObservation("Dark / Moody", "Dark / Moody", 0.82, True),
        ConfidenceObservation("Dark / Moody", "Blue", 0.88, False),
    )
    calibrator = ConfidenceCalibrator(bins=2).fit(observations)
    assert calibrator.transform(0.25) == 0.5
    assert calibrator.transform(0.85) == 0.5
    assert len(calibrator.bins_report) == 2


def test_empty_calibrator_preserves_input() -> None:
    calibrator = ConfidenceCalibrator().fit(())
    assert calibrator.transform(0.73) == 0.73
