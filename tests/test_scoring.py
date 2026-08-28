from dtc_log_intelligence.diagnosis.diagnose import Diagnosis
from dtc_log_intelligence.evaluation.scoring import evaluate


def _diag(session_id: str, root_cause: str, parse_ok: bool = True) -> Diagnosis:
    return Diagnosis(
        session_id=session_id, root_cause=root_cause, confidence=0.9,
        reasoning="test", recommended_action="test", raw_response="{}", parse_ok=parse_ok,
    )


def test_perfect_predictions_score_100_percent():
    gt = {"s1": "healthy", "s2": "misfire_cascade"}
    diagnoses = {"s1": _diag("s1", "healthy"), "s2": _diag("s2", "misfire_cascade")}
    report = evaluate(gt, diagnoses)
    assert report.accuracy == 1.0
    assert report.correct == 2


def test_wrong_prediction_counted_in_confusion_matrix():
    gt = {"s1": "sensor_drift"}
    diagnoses = {"s1": _diag("s1", "cooling_failure")}
    report = evaluate(gt, diagnoses)
    assert report.accuracy == 0.0
    assert report.confusion["sensor_drift"]["cooling_failure"] == 1
    assert len(report.misses) == 1


def test_unparseable_diagnosis_counts_as_a_miss_not_excluded():
    gt = {"s1": "healthy"}
    diagnoses = {"s1": _diag("s1", "unparseable", parse_ok=False)}
    report = evaluate(gt, diagnoses)
    assert report.total == 1
    assert report.accuracy == 0.0


def test_missing_diagnosis_counts_as_no_diagnosis_miss():
    gt = {"s1": "healthy"}
    report = evaluate(gt, {})
    assert report.confusion["healthy"]["no_diagnosis"] == 1


def test_per_class_accuracy_computed_independently():
    gt = {"s1": "healthy", "s2": "healthy", "s3": "sensor_drift"}
    diagnoses = {
        "s1": _diag("s1", "healthy"),
        "s2": _diag("s2", "healthy"),
        "s3": _diag("s3", "cooling_failure"),
    }
    report = evaluate(gt, diagnoses)
    per_class = report.per_class_accuracy()
    assert per_class["healthy"] == 1.0
    assert per_class["sensor_drift"] == 0.0
