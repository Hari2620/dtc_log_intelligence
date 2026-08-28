"""Ties episode summarization, prompting, and the provider call together,
and handles the one failure mode that matters most for a JSON-contract
prompt: a model that doesn't actually return clean JSON (wraps it in prose,
fences it in markdown, or just gets it wrong). `parse_ok=False` results still
get a `root_cause` of "unparseable" rather than being silently dropped -- the
eval harness scores that as a miss, not as an excluded sample (see README).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from dtc_log_intelligence.diagnosis.episodes import summarize
from dtc_log_intelligence.diagnosis.prompts import CANDIDATE_LABELS, build_prompt
from dtc_log_intelligence.diagnosis.providers import LlmProvider
from dtc_log_intelligence.domain import SessionLog
from dtc_log_intelligence.knowledge.manual import DtcDefinition

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Diagnosis:
    session_id: str
    root_cause: str
    confidence: float
    reasoning: str
    recommended_action: str
    raw_response: str
    parse_ok: bool


def _extract_json(raw: str) -> dict | None:
    """Tolerant extraction: find the first {...} block (handles markdown code
    fences and stray prose around the JSON) and try to parse it."""
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def diagnose_session(session: SessionLog, manual: dict[str, DtcDefinition], provider: LlmProvider) -> Diagnosis:
    summary = summarize(session)
    prompt = build_prompt(summary, manual)
    raw = provider.complete(prompt)

    parsed = _extract_json(raw)
    if parsed is None:
        return Diagnosis(
            session_id=session.session_id, root_cause="unparseable", confidence=0.0,
            reasoning="Provider response did not contain a parseable JSON object.",
            recommended_action="", raw_response=raw, parse_ok=False,
        )

    root_cause = parsed.get("root_cause", "unparseable")
    if root_cause not in CANDIDATE_LABELS:
        root_cause = "other"

    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    return Diagnosis(
        session_id=session.session_id,
        root_cause=root_cause,
        confidence=confidence,
        reasoning=str(parsed.get("reasoning", "")),
        recommended_action=str(parsed.get("recommended_action", "")),
        raw_response=raw,
        parse_ok=True,
    )
