"""End-to-end entry point: generate synthetic sessions, parse them back out,
run the diagnosis layer over each one, grade against ground truth, write a
report. Every phase's output lands in --out-dir so you can inspect the raw
traces, the parsed records, and the model's reasoning independently instead
of only seeing the final accuracy number.

Usage:
    python -m dtc_log_intelligence.cli run --sessions 60 --seed 7 --provider mock --out-dir data/run1
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from dtc_log_intelligence.diagnosis.diagnose import diagnose_session
from dtc_log_intelligence.diagnosis.providers import build_provider
from dtc_log_intelligence.domain import SessionLog
from dtc_log_intelligence.evaluation.scoring import evaluate
from dtc_log_intelligence.generator.synth import generate_run
from dtc_log_intelligence.knowledge.manual import load_manual
from dtc_log_intelligence.parser.dtc_parser import parse_dtc_file
from dtc_log_intelligence.parser.uds_parser import parse_uds_file
from dtc_log_intelligence.report import render_markdown


def run(num_sessions: int, seed: int, provider_name: str, out_dir: Path) -> None:
    print(f"Generating {num_sessions} synthetic sessions (seed={seed})...")
    ground_truth = generate_run(num_sessions, seed, out_dir)

    manual = load_manual()
    provider = build_provider(provider_name)
    print(f"Diagnosing with provider={provider_name}...")

    diagnoses = {}
    parse_warnings: list[str] = []
    for session_id in ground_truth:
        session_dir = out_dir / session_id
        dtc_result = parse_dtc_file(session_dir / "dtc_trace.log", session_id)
        uds_result = parse_uds_file(session_dir / "uds_trace.log", session_id)
        parse_warnings.extend(dtc_result.warnings)
        parse_warnings.extend(uds_result.warnings)

        session = SessionLog(session_id=session_id, dtc_records=dtc_result.records, uds_frames=uds_result.frames)
        diagnoses[session_id] = diagnose_session(session, manual, provider)

    if parse_warnings:
        print(f"  {len(parse_warnings)} parse warnings (see parse_warnings.log)")
        (out_dir / "parse_warnings.log").write_text("\n".join(parse_warnings) + "\n")

    (out_dir / "diagnoses.json").write_text(
        json.dumps({sid: asdict(d) for sid, d in diagnoses.items()}, indent=2)
    )

    report = evaluate(ground_truth, diagnoses)
    report_md = render_markdown(report, provider_name, num_sessions)
    (out_dir / "report.md").write_text(report_md)

    print(f"\nOverall accuracy: {report.accuracy:.1%} ({report.correct}/{report.total})")
    print(f"Report written to {out_dir / 'report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="DTC Log Intelligence -- generate, diagnose, evaluate.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the full generate -> parse -> diagnose -> evaluate pipeline.")
    run_parser.add_argument("--sessions", type=int, default=60)
    run_parser.add_argument("--seed", type=int, default=7)
    run_parser.add_argument("--provider", choices=["mock", "anthropic"], default="mock")
    run_parser.add_argument("--out-dir", type=Path, default=Path("data/run1"))

    args = parser.parse_args()
    if args.command == "run":
        run(args.sessions, args.seed, args.provider, args.out_dir)


if __name__ == "__main__":
    main()
