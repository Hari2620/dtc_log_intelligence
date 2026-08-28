"""Loads the illustrative DTC manual bundled with the package.

This is a hand-curated set of ~10 generic (SAE J2012) code definitions, not a
scrape or transcription of any real OEM service manual -- deliberately, both
to sidestep any IP question and because the generic definitions are what the
synthetic generator actually uses, so the manual and the data agree by
construction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

_MANUAL_PATH = Path(__file__).parent / "dtc_manual.json"


class DtcDefinition(TypedDict):
    title: str
    typical_causes: list[str]


def load_manual() -> dict[str, DtcDefinition]:
    return json.loads(_MANUAL_PATH.read_text())


def lookup(code: str, manual: dict[str, DtcDefinition] | None = None) -> DtcDefinition | None:
    manual = manual if manual is not None else load_manual()
    return manual.get(code)
