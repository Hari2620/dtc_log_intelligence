"""Shared vocabulary for the whole pipeline: what a DTC snapshot and a UDS
frame look like, and the closed set of root causes the generator can produce
and the diagnosis layer is asked to choose from.

Keeping this a closed set (rather than open-ended free text) is deliberate —
see README "decisions and trade-offs". It's what makes automated grading
possible: there's no fuzzy-matching a free-text diagnosis against a free-text
ground truth, just an exact label comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FaultClass(str, Enum):
    HEALTHY = "healthy"
    MISFIRE_CASCADE = "misfire_cascade"
    COOLING_FAILURE = "cooling_failure"
    NETWORK_DROPOUT = "network_dropout"
    SENSOR_DRIFT = "sensor_drift"


@dataclass
class FreezeFrame:
    """Sensor snapshot captured when a DTC's status changed — the same handful
    of parameters the Mahale et al. OBD-II dataset uses (RPM, coolant temp,
    throttle position, engine load, MAF, fuel trim), because those are the
    signals that actually distinguish these fault classes from each other.
    """

    rpm: float | None
    coolant_temp_c: float | None
    throttle_pct: float | None
    engine_load_pct: float | None
    maf_g_s: float | None
    fuel_trim_pct: float | None


@dataclass
class DtcRecord:
    """One DTC observation: a code plus its SAE J2012 status byte and the
    freeze frame captured at that moment. `status_byte` bit 2 (0x04) means
    pending, bit 3 (0x08) means confirmed — the generator flips pending to
    confirmed partway through a session, which is itself a diagnostic signal
    (a code that's been pending for a while and just confirmed reads
    differently than one that's been confirmed from the first poll).
    """

    session_id: str
    timestamp: str  # ISO 8601
    ecu: str
    code: str  # e.g. "P0301"
    status_byte: int
    freeze_frame: FreezeFrame

    @property
    def confirmed(self) -> bool:
        return bool(self.status_byte & 0x08)

    @property
    def pending(self) -> bool:
        return bool(self.status_byte & 0x04)


@dataclass
class UdsFrame:
    """One UDS (ISO 14229) request or response. `nrc` is set only on a
    negative response (service byte 0x7F) — "timeout" is a synthetic NRC this
    generator uses to stand in for "the ECU never answered at all," which is
    how an intermittent bus fault actually looks on a trace, as opposed to a
    real NRC like 0x11 (serviceNotSupported).
    """

    session_id: str
    timestamp: str
    direction: str  # "request" | "response"
    service_id: str  # e.g. "0x19"
    sub_function: str | None
    data: str | None
    nrc: str | None = None


@dataclass
class SessionLog:
    """Everything captured for one diagnostic session — the unit the
    diagnosis layer reasons over and the unit the eval harness grades."""

    session_id: str
    dtc_records: list[DtcRecord] = field(default_factory=list)
    uds_frames: list[UdsFrame] = field(default_factory=list)
