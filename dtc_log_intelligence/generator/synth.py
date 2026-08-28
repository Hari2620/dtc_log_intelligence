"""Orchestrates fault-class selection and writes each session's raw traces to
disk. `ground_truth.json` is written alongside the sessions but is never read
by the parser or diagnosis layer — only by the evaluation harness — the same
way a real held-out label set would be kept separate from what a diagnostic
tool actually gets to see.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dtc_log_intelligence.domain import FaultClass
from dtc_log_intelligence.generator.faults import GENERATORS

DEFAULT_WEIGHTS: dict[FaultClass, float] = {
    FaultClass.HEALTHY: 0.2,
    FaultClass.MISFIRE_CASCADE: 0.2,
    FaultClass.COOLING_FAILURE: 0.2,
    FaultClass.NETWORK_DROPOUT: 0.2,
    FaultClass.SENSOR_DRIFT: 0.2,
}


def generate_run(num_sessions: int, seed: int, out_dir: Path) -> dict[str, str]:
    """Writes <out_dir>/session_NNN/{dtc_trace.log,uds_trace.log} for each
    session plus <out_dir>/ground_truth.json. Returns the ground truth dict
    (session_id -> FaultClass value) for convenience.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    master_rng = random.Random(seed)
    classes = list(DEFAULT_WEIGHTS.keys())
    weights = list(DEFAULT_WEIGHTS.values())

    ground_truth: dict[str, str] = {}

    for i in range(num_sessions):
        session_id = f"session_{i:03d}"
        fault_class: FaultClass = master_rng.choices(classes, weights=weights, k=1)[0]
        # Deterministic per-session seed so a single session can be regenerated
        # in isolation and still match a full-run output byte for byte.
        session_rng = random.Random(seed * 1_000_003 + i)
        base_time = datetime(2026, 8, 28, 9, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=i * 3)

        dtc_lines, uds_lines = GENERATORS[fault_class](session_rng, session_id, base_time)

        session_dir = out_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "dtc_trace.log").write_text("\n".join(dtc_lines) + "\n")
        (session_dir / "uds_trace.log").write_text("\n".join(uds_lines) + "\n")

        ground_truth[session_id] = fault_class.value

    (out_dir / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2))
    return ground_truth
