"""Parses uds_trace.log into UdsFrame objects.

Three response shapes to distinguish: a positive response (SID is the
request SID + 0x40, per ISO 14229), a negative response (SID=0x7F, carrying
the original REQ_SID and an NRC), and this generator's synthetic stand-in for
"the ECU never answered" (TIMEOUT=1) -- represented as an NRC of "timeout" so
downstream code can treat every failure mode as "check the NRC field" instead
of needing a special case for silence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dtc_log_intelligence.domain import UdsFrame
from dtc_log_intelligence.parser.common import LineParseError, tokenize_line


@dataclass
class ParseResult:
    frames: list[UdsFrame]
    warnings: list[str]


def parse_uds_lines(lines: list[str], session_id: str) -> ParseResult:
    frames: list[UdsFrame] = []
    warnings: list[str] = []

    for line_no, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            timestamp, tokens = tokenize_line(raw_line)
            direction = tokens["DIR"]
            ecu = tokens.get("ECU", "unknown")

            if tokens.get("TIMEOUT") == "1":
                frames.append(UdsFrame(
                    session_id=session_id, timestamp=timestamp, direction=direction,
                    service_id="none", sub_function=None, data=None, nrc="timeout",
                ))
                continue

            service_id = tokens["SID"]
            if service_id == "0x7F":
                frames.append(UdsFrame(
                    session_id=session_id, timestamp=timestamp, direction=direction,
                    service_id=tokens["REQ_SID"], sub_function=None, data=None,
                    nrc=tokens["NRC"],
                ))
                continue

            frames.append(UdsFrame(
                session_id=session_id, timestamp=timestamp, direction=direction,
                service_id=service_id, sub_function=tokens.get("SUB"), data=tokens.get("DATA"),
            ))
        except (LineParseError, KeyError) as exc:
            warnings.append(f"uds_trace.log:{line_no}: {exc}")

    return ParseResult(frames=frames, warnings=warnings)


def parse_uds_file(path: Path, session_id: str) -> ParseResult:
    return parse_uds_lines(path.read_text().splitlines(), session_id)
