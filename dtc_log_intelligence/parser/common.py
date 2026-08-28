"""Shared line tokenizer for both trace formats: `[timestamp] KEY=VALUE ...`.

A malformed line is a fact of life for anything that ingests logs from the
field — this raises `LineParseError` rather than crashing the whole file, and
both parsers catch it per-line and collect warnings instead of aborting (see
`ParseResult` in dtc_parser.py / uds_parser.py).
"""

from __future__ import annotations

import re

_LINE_RE = re.compile(r"^\[(?P<timestamp>[^\]]+)\]\s*(?P<rest>.*)$")
_TOKEN_RE = re.compile(r"(\w+)=(\S+)")


class LineParseError(ValueError):
    pass


def tokenize_line(line: str) -> tuple[str, dict[str, str]]:
    match = _LINE_RE.match(line.strip())
    if not match:
        raise LineParseError(f"line does not start with a [timestamp]: {line!r}")

    timestamp = match.group("timestamp")
    tokens = dict(_TOKEN_RE.findall(match.group("rest")))
    if not tokens:
        raise LineParseError(f"no KEY=VALUE tokens found: {line!r}")

    return timestamp, tokens
