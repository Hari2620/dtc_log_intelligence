"""Parses dtc_trace.log into DtcRecord objects.

A line with DTC=NONE means "polled, nothing active" -- it's real signal (the
session was alive and checked) but it isn't a fault observation, so it does
not produce a DtcRecord. Everything else does, with whatever freeze-frame
fields happen to be present -- during a network-dropout session most of them
are simply absent, and FreezeFrame tolerates that (all fields optional).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dtc_log_intelligence.domain import DtcRecord, FreezeFrame
from dtc_log_intelligence.parser.common import LineParseError, tokenize_line

_FRAME_KEYS = {
    "RPM": "rpm",
    "COOLANT_C": "coolant_temp_c",
    "TPS_PCT": "throttle_pct",
    "LOAD_PCT": "engine_load_pct",
    "MAF_GS": "maf_g_s",
    "STFT_PCT": "fuel_trim_pct",
}


@dataclass
class ParseResult:
    records: list[DtcRecord]
    warnings: list[str]


def _parse_frame(tokens: dict[str, str]) -> FreezeFrame:
    values: dict[str, float | None] = {field_name: None for field_name in _FRAME_KEYS.values()}
    for raw_key, field_name in _FRAME_KEYS.items():
        if raw_key in tokens:
            values[field_name] = float(tokens[raw_key])
    return FreezeFrame(**values)


def parse_dtc_lines(lines: list[str], session_id: str) -> ParseResult:
    records: list[DtcRecord] = []
    warnings: list[str] = []

    for line_no, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            timestamp, tokens = tokenize_line(raw_line)
            code = tokens["DTC"]
            if code == "NONE":
                continue

            ecu = tokens.get("ECU", "unknown")
            status_byte = int(tokens["STATUS"], 16)
            frame = _parse_frame(tokens)

            records.append(DtcRecord(
                session_id=session_id,
                timestamp=timestamp,
                ecu=ecu,
                code=code,
                status_byte=status_byte,
                freeze_frame=frame,
            ))
        except (LineParseError, KeyError, ValueError) as exc:
            warnings.append(f"dtc_trace.log:{line_no}: {exc}")

    return ParseResult(records=records, warnings=warnings)


def parse_dtc_file(path: Path, session_id: str) -> ParseResult:
    return parse_dtc_lines(path.read_text().splitlines(), session_id)
