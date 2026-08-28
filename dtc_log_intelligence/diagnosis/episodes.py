"""Condenses a full SessionLog (potentially dozens of raw lines) into the
handful of facts that actually matter for diagnosis: which codes appeared and
how their status progressed, the shape of each freeze-frame trend (not just
its final value -- a monotonic climb reads differently than a noisy one, and
that difference is the whole point of the sensor-drift fault class), and how
the UDS session behaved.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dtc_log_intelligence.domain import SessionLog


@dataclass
class CodeStatus:
    pending_count: int = 0
    confirmed_count: int = 0


@dataclass
class TrendSummary:
    first: float
    last: float
    min: float
    max: float
    count: int

    @property
    def monotonic(self) -> bool:
        """True if every step moved in the same direction as the first step --
        a clean ramp. False for a noisy/erratic series, even if it trends the
        same overall direction."""
        return self._monotonic

    _monotonic: bool = field(default=True, repr=False)


@dataclass
class EpisodeSummary:
    session_id: str
    code_status: dict[str, CodeStatus]
    freeze_frame_trends: dict[str, TrendSummary]
    uds_anomaly_counts: dict[str, int]
    uds_total_frames: int


def _trend(values: list[float]) -> TrendSummary:
    monotonic = all(b >= a for a, b in zip(values, values[1:])) or all(b <= a for a, b in zip(values, values[1:]))
    return TrendSummary(first=values[0], last=values[-1], min=min(values), max=max(values), count=len(values), _monotonic=monotonic)


def summarize(session: SessionLog) -> EpisodeSummary:
    code_status: dict[str, CodeStatus] = {}
    for record in session.dtc_records:
        status = code_status.setdefault(record.code, CodeStatus())
        if record.confirmed:
            status.confirmed_count += 1
        elif record.pending:
            status.pending_count += 1

    frame_values: dict[str, list[float]] = {}
    for record in session.dtc_records:
        for field_name, value in record.freeze_frame.__dict__.items():
            if value is not None:
                frame_values.setdefault(field_name, []).append(value)

    freeze_frame_trends = {name: _trend(values) for name, values in frame_values.items() if len(values) >= 2}

    uds_anomaly_counts: dict[str, int] = {}
    for frame in session.uds_frames:
        if frame.nrc:
            uds_anomaly_counts[frame.nrc] = uds_anomaly_counts.get(frame.nrc, 0) + 1

    return EpisodeSummary(
        session_id=session.session_id,
        code_status=code_status,
        freeze_frame_trends=freeze_frame_trends,
        uds_anomaly_counts=uds_anomaly_counts,
        uds_total_frames=len(session.uds_frames),
    )
