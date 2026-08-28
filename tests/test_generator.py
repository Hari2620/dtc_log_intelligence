from pathlib import Path

from dtc_log_intelligence.generator.synth import generate_run


def test_generation_is_deterministic_for_a_given_seed(tmp_path: Path):
    gt_a = generate_run(num_sessions=20, seed=42, out_dir=tmp_path / "a")
    gt_b = generate_run(num_sessions=20, seed=42, out_dir=tmp_path / "b")

    assert gt_a == gt_b
    for session_id in gt_a:
        a_dtc = (tmp_path / "a" / session_id / "dtc_trace.log").read_text()
        b_dtc = (tmp_path / "b" / session_id / "dtc_trace.log").read_text()
        assert a_dtc == b_dtc


def test_different_seeds_produce_different_runs(tmp_path: Path):
    gt_a = generate_run(num_sessions=20, seed=1, out_dir=tmp_path / "a")
    gt_b = generate_run(num_sessions=20, seed=2, out_dir=tmp_path / "b")

    assert gt_a != gt_b


def test_all_fault_classes_appear_over_enough_sessions(tmp_path: Path):
    gt = generate_run(num_sessions=100, seed=99, out_dir=tmp_path / "run")
    assert set(gt.values()) == {
        "healthy", "misfire_cascade", "cooling_failure", "network_dropout", "sensor_drift",
    }


def test_ground_truth_file_matches_returned_dict(tmp_path: Path):
    import json
    gt = generate_run(num_sessions=10, seed=5, out_dir=tmp_path / "run")
    on_disk = json.loads((tmp_path / "run" / "ground_truth.json").read_text())
    assert on_disk == gt
