"""The two-step chain-of-thought prompt: interpret what was observed, then
map it to one of a closed set of root causes. Closed-set on purpose (see
domain.py) -- the model is told exactly which labels are acceptable and
asked to return JSON, not prose, so the response can be graded automatically.
"""

from __future__ import annotations

from dtc_log_intelligence.diagnosis.episodes import EpisodeSummary
from dtc_log_intelligence.domain import FaultClass
from dtc_log_intelligence.knowledge.manual import DtcDefinition

CANDIDATE_LABELS = [f.value for f in FaultClass] + ["other"]


def _format_manual_entries(codes: list[str], manual: dict[str, DtcDefinition]) -> str:
    lines = []
    for code in codes:
        entry = manual.get(code)
        if entry:
            causes = ", ".join(entry["typical_causes"])
            lines.append(f"  {code} -- {entry['title']}. Typical causes: {causes}.")
        else:
            lines.append(f"  {code} -- not in the manual (unrecognized code).")
    return "\n".join(lines) if lines else "  (no DTCs observed this session)"


def _format_trends(summary: EpisodeSummary) -> str:
    if not summary.freeze_frame_trends:
        return "  (no freeze-frame telemetry available this session -- likely a comms issue)"
    lines = []
    for name, trend in summary.freeze_frame_trends.items():
        shape = "a smooth, steady ramp" if trend.monotonic else "noisy / non-monotonic"
        lines.append(f"  {name}: {trend.first:.1f} -> {trend.last:.1f} over {trend.count} polls "
                      f"(range {trend.min:.1f}-{trend.max:.1f}, {shape})")
    return "\n".join(lines)


def _format_uds(summary: EpisodeSummary) -> str:
    if not summary.uds_anomaly_counts:
        return f"  {summary.uds_total_frames} UDS frames exchanged, no negative responses or timeouts."
    parts = ", ".join(f"{count}x {code}" for code, count in summary.uds_anomaly_counts.items())
    return f"  {summary.uds_total_frames} UDS frames exchanged, with anomalies: {parts}."


def build_prompt(summary: EpisodeSummary, manual: dict[str, DtcDefinition]) -> str:
    codes = list(summary.code_status.keys())
    code_lines = []
    for code, status in summary.code_status.items():
        code_lines.append(f"  {code}: seen pending {status.pending_count}x, confirmed {status.confirmed_count}x")

    return f"""You are a vehicle diagnostic assistant reviewing one diagnostic session's data.

DTC codes observed this session:
{chr(10).join(code_lines) if code_lines else "  (none)"}

Manual entries for those codes:
{_format_manual_entries(codes, manual)}

Freeze-frame sensor trends across the session:
{_format_trends(summary)}

UDS (diagnostic bus) behavior:
{_format_uds(summary)}

Step 1: In one or two sentences, summarize what these observations suggest is
physically happening -- pay attention to whether trends are smooth/monotonic
or noisy, since a real thermal or mechanical fault usually produces a
different trend shape than a failing sensor does, and whether the freeze
frame data is present at all (its total absence is itself a signal).

Step 2: Choose exactly one root cause from this list: {", ".join(CANDIDATE_LABELS)}.
Respond with ONLY a JSON object, no other text, in this exact shape:
{{"root_cause": "<one of the labels above>", "confidence": <0.0-1.0>, "reasoning": "<your step 1 summary>", "recommended_action": "<one concrete next diagnostic step>"}}
"""
