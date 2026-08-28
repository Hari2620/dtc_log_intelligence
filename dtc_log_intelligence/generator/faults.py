"""One generation function per fault class. Each returns the raw text lines
for a session's DTC trace and UDS trace, plus the ground truth is simply
"whichever function generated this" — the caller (synth.py) tags it.

These are hand-tuned parameter ranges grounded in what the generic OBD-II
code definitions and ISO 14229 actually mean, not a learned distribution —
see README for why that's a deliberate simplification of the CTGAN approach
in the Mahale et al. paper rather than an attempt to reproduce it.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from dtc_log_intelligence.domain import FaultClass

POLL_INTERVAL_S = 4
SESSION_POLLS = 20


def _ts(base: datetime, poll_index: int, jitter: random.Random) -> str:
    t = base + timedelta(seconds=poll_index * POLL_INTERVAL_S + jitter.uniform(-0.3, 0.3))
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _dtc_line(ts: str, ecu: str, code: str, status: int, frame: dict[str, float | None] | None = None) -> str:
    parts = [f"[{ts}]", f"ECU={ecu}", f"DTC={code}", f"STATUS=0x{status:02X}"]
    if frame:
        for key, value in frame.items():
            if value is not None:
                parts.append(f"{key}={value:.1f}")
    return " ".join(parts)


def _uds_request(ts: str, ecu: str, sid: str, sub: str | None, data: str | None) -> str:
    parts = [f"[{ts}]", "DIR=TX", f"ECU={ecu}", f"SID={sid}"]
    if sub:
        parts.append(f"SUB={sub}")
    if data:
        parts.append(f"DATA={data}")
    return " ".join(parts)


def _uds_positive(ts: str, ecu: str, sid: str, sub: str | None, data: str) -> str:
    parts = [f"[{ts}]", "DIR=RX", f"ECU={ecu}", f"SID={sid}"]
    if sub:
        parts.append(f"SUB={sub}")
    parts.append(f"DATA={data}")
    return " ".join(parts)


def _uds_negative(ts: str, ecu: str, req_sid: str, nrc: str) -> str:
    return f"[{ts}] DIR=RX ECU={ecu} SID=0x7F REQ_SID={req_sid} NRC={nrc}"


def _uds_timeout(ts: str, ecu: str) -> str:
    return f"[{ts}] DIR=RX ECU={ecu} TIMEOUT=1"


def _routine_uds_poll(rng: random.Random, base: datetime, poll_index: int, tester: str, ecu: str) -> list[str]:
    """A normal ReadDTCInformation(reportDTCByStatusMask) round trip."""
    ts_req = _ts(base, poll_index, rng)
    ts_resp = _ts(base, poll_index, rng)
    lines = [_uds_request(ts_req, tester, "0x19", "0x02", "0xFF")]
    lines.append(_uds_positive(ts_resp, ecu, "0x59", "0x02", "0803010800000000"))
    return lines


def generate_healthy(rng: random.Random, session_id: str, base: datetime) -> tuple[list[str], list[str]]:
    tester, ecu = "0x7E0", "0x7E8"
    dtc_lines, uds_lines = [], []
    for i in range(SESSION_POLLS):
        ts = _ts(base, i, rng)
        dtc_lines.append(_dtc_line(ts, tester, "NONE", 0x00))
        if i % 5 == 0:
            uds_lines.extend(_routine_uds_poll(rng, base, i, tester, ecu))
    return dtc_lines, uds_lines


def generate_misfire_cascade(rng: random.Random, session_id: str, base: datetime) -> tuple[list[str], list[str]]:
    tester, ecu = "0x7E0", "0x7E8"
    dtc_lines, uds_lines = [], []
    cylinders = rng.sample(["P0301", "P0302", "P0303", "P0304"], k=rng.randint(1, 3))
    confirm_at = rng.randint(6, 10)
    rpm_base = rng.uniform(750, 900)
    for i in range(SESSION_POLLS):
        ts = _ts(base, i, rng)
        rpm = rpm_base + rng.uniform(-180, 220)  # unstable idle
        frame = {
            "RPM": rpm,
            "COOLANT_C": rng.uniform(85, 95),
            "TPS_PCT": rng.uniform(8, 16),
            "LOAD_PCT": rng.uniform(30, 45),
            "MAF_GS": rng.uniform(5.5, 7.5),
            "STFT_PCT": rng.uniform(-3, 3),
        }
        status = 0x04 if i < confirm_at else 0x08
        dtc_lines.append(_dtc_line(ts, tester, "P0300", status, frame))
        for code in cylinders:
            dtc_lines.append(_dtc_line(ts, tester, code, status, frame))
        if i % 5 == 0:
            uds_lines.extend(_routine_uds_poll(rng, base, i, tester, ecu))
    return dtc_lines, uds_lines


def generate_cooling_failure(rng: random.Random, session_id: str, base: datetime) -> tuple[list[str], list[str]]:
    tester, ecu = "0x7E0", "0x7E8"
    dtc_lines, uds_lines = [], []
    confirm_at = rng.randint(8, 12)
    coolant = rng.uniform(88, 94)
    for i in range(SESSION_POLLS):
        ts = _ts(base, i, rng)
        coolant += rng.uniform(1.8, 2.6)  # strictly increasing -- a clean, real thermal ramp
        derate = coolant > 118
        frame = {
            "RPM": rng.uniform(700, 850) if not derate else rng.uniform(600, 700),
            "COOLANT_C": coolant,
            "TPS_PCT": rng.uniform(8, 14),
            "LOAD_PCT": rng.uniform(28, 38),
            "MAF_GS": rng.uniform(5.0, 6.5),
            "STFT_PCT": rng.uniform(-2, 2),
        }
        status = 0x04 if i < confirm_at else 0x08
        code = "P0217" if coolant > 110 else "P0128"
        dtc_lines.append(_dtc_line(ts, tester, code, status, frame))
        if i % 5 == 0:
            uds_lines.extend(_routine_uds_poll(rng, base, i, tester, ecu))
    return dtc_lines, uds_lines


def generate_network_dropout(rng: random.Random, session_id: str, base: datetime) -> tuple[list[str], list[str]]:
    tester, ecu = "0x7E0", "0x7E8"
    dtc_lines, uds_lines = [], []
    confirm_at = rng.randint(5, 8)
    for i in range(SESSION_POLLS):
        ts = _ts(base, i, rng)
        # Telemetry drops out entirely during a comm loss window -- no freeze frame available.
        status = 0x04 if i < confirm_at else 0x08
        dtc_lines.append(_dtc_line(ts, tester, "U0100", status, frame=None))
        if rng.random() < 0.4:
            dtc_lines.append(_dtc_line(ts, tester, "U0101", status, frame=None))

        req_ts = _ts(base, i, rng)
        resp_ts = _ts(base, i, rng)
        uds_lines.append(_uds_request(req_ts, tester, "0x19", "0x02", "0xFF"))
        roll = rng.random()
        if roll < 0.35:
            uds_lines.append(_uds_timeout(resp_ts, ecu))
        elif roll < 0.55:
            uds_lines.append(_uds_negative(resp_ts, ecu, "0x19", "0x11"))
        else:
            uds_lines.append(_uds_positive(resp_ts, ecu, "0x59", "0x02", "0803010800000000"))
    return dtc_lines, uds_lines


def _generate_fuel_trim_drift(rng: random.Random, tester: str, ecu: str, base: datetime, lean: bool) -> tuple[list[str], list[str]]:
    dtc_lines, uds_lines = [], []
    code = "P0171" if lean else "P0172"
    confirm_at = rng.randint(12, 16)  # slow to confirm -- it's a *drift*, not a hard fault
    trim_start = rng.uniform(-2, 2)
    sign = 1 if lean else -1
    for i in range(SESSION_POLLS):
        ts = _ts(base, i, rng)
        trim = trim_start + sign * i * rng.uniform(0.9, 1.4)  # slow monotonic drift
        frame = {
            "RPM": rng.uniform(720, 820),
            "COOLANT_C": rng.uniform(88, 94),
            "TPS_PCT": rng.uniform(8, 14),
            "LOAD_PCT": rng.uniform(28, 36),
            "MAF_GS": rng.uniform(5.2, 6.8),
            "STFT_PCT": trim,
        }
        if abs(trim) > 8:
            status = 0x04 if i < confirm_at else 0x08
            dtc_lines.append(_dtc_line(ts, tester, code, status, frame))
        else:
            dtc_lines.append(_dtc_line(ts, tester, "NONE", 0x00, frame))
        if i % 5 == 0:
            uds_lines.extend(_routine_uds_poll(rng, base, i, tester, ecu))
    return dtc_lines, uds_lines


def _generate_coolant_sensor_drift(rng: random.Random, tester: str, ecu: str, base: datetime) -> tuple[list[str], list[str]]:
    """The deliberately hard case: this emits the SAME code (P0128) that
    generate_cooling_failure emits, and the reading climbs too -- but here the
    engine is fine. RPM stays flat (no derate, because there's no real heat to
    protect against) and the reading is noisier/less smooth than a genuine
    thermal rise, rather than the clean monotonic climb a real cooling failure
    produces. A code-only lookup cannot tell these two apart; only reading the
    shape of the trend and the RPM/load correlation can. That gap is the
    entire point of this fault class existing (see README).
    """
    dtc_lines, uds_lines = [], []
    confirm_at = rng.randint(12, 16)
    coolant = rng.uniform(88, 94)
    for i in range(SESSION_POLLS):
        ts = _ts(base, i, rng)
        coolant += rng.uniform(-1.5, 4.0)  # noisy drift, not a clean ramp
        frame = {
            "RPM": rng.uniform(740, 820),  # flat -- no derate, no real thermal stress
            "COOLANT_C": coolant,
            "TPS_PCT": rng.uniform(8, 14),
            "LOAD_PCT": rng.uniform(28, 36),
            "MAF_GS": rng.uniform(5.2, 6.8),
            "STFT_PCT": rng.uniform(-2, 2),
        }
        if coolant > 108:
            status = 0x04 if i < confirm_at else 0x08
            dtc_lines.append(_dtc_line(ts, tester, "P0128", status, frame))
        else:
            dtc_lines.append(_dtc_line(ts, tester, "NONE", 0x00, frame))
        if i % 5 == 0:
            uds_lines.extend(_routine_uds_poll(rng, base, i, tester, ecu))
    return dtc_lines, uds_lines


def generate_sensor_drift(rng: random.Random, session_id: str, base: datetime) -> tuple[list[str], list[str]]:
    tester, ecu = "0x7E0", "0x7E8"
    variant = rng.choice(["lean", "rich", "coolant_sensor"])
    if variant == "coolant_sensor":
        return _generate_coolant_sensor_drift(rng, tester, ecu, base)
    return _generate_fuel_trim_drift(rng, tester, ecu, base, lean=(variant == "lean"))


GENERATORS = {
    FaultClass.HEALTHY: generate_healthy,
    FaultClass.MISFIRE_CASCADE: generate_misfire_cascade,
    FaultClass.COOLING_FAILURE: generate_cooling_failure,
    FaultClass.NETWORK_DROPOUT: generate_network_dropout,
    FaultClass.SENSOR_DRIFT: generate_sensor_drift,
}
