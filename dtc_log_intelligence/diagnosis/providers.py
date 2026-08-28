"""Same pluggable-provider shape as Repo 1's ILlmProvider, reimplemented here
in Python rather than shared as a package -- these repos are meant to be read
standalone (see README trade-offs).

MockLlmProvider is not a stand-in for "no answer" -- it's a real, if naive,
baseline: a fixed code -> fault-class lookup table with no notion of trend,
freeze-frame shape, or UDS context. It exists so the eval report can state a
number for "what you get with no LLM at all," which is the honest bar a real
LLM-based diagnosis has to clear to justify the extra latency and cost.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol

import httpx

# Deliberately ambiguous: P0128 is mapped to cooling_failure here, but the
# generator also emits P0128 for the sensor-drift "coolant sensor" variant
# (see generator/faults.py). This lookup table has no way to know which one
# it's looking at -- that's the entire point of that fault class existing.
_NAIVE_CODE_TO_FAULT_CLASS = {
    "P0300": "misfire_cascade", "P0301": "misfire_cascade", "P0302": "misfire_cascade",
    "P0303": "misfire_cascade", "P0304": "misfire_cascade",
    "P0217": "cooling_failure", "P0128": "cooling_failure",
    "P0171": "sensor_drift", "P0172": "sensor_drift",
    "U0100": "network_dropout", "U0101": "network_dropout",
}


class LlmProvider(Protocol):
    name: str

    def complete(self, prompt: str, max_tokens: int = 1024) -> str: ...


class MockLlmProvider:
    name = "mock"

    def complete(self, prompt: str, max_tokens: int = 1024) -> str:
        codes_seen = re.findall(r"\b([PU]0\d{3})\b", prompt)
        if not codes_seen:
            root_cause = "healthy"
        else:
            root_cause = _NAIVE_CODE_TO_FAULT_CLASS.get(codes_seen[0], "other")

        return json.dumps({
            "root_cause": root_cause,
            "confidence": 0.5,
            "reasoning": f"Naive lookup: first DTC code observed was {codes_seen[0] if codes_seen else 'none'}; "
                         f"mapped via a fixed code table with no trend or UDS context considered.",
            "recommended_action": "Confirm with a full diagnostic scan before proceeding.",
        })


class AnthropicLlmProvider:
    name = "anthropic"

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic.")
        self._api_key = api_key
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        self._client = httpx.Client(
            base_url="https://api.anthropic.com",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=30.0,
        )

    def complete(self, prompt: str, max_tokens: int = 1024) -> str:
        response = self._client.post("/v1/messages", json={
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        })
        response.raise_for_status()
        return response.json()["content"][0]["text"]


def build_provider(name: str) -> LlmProvider:
    if name == "anthropic":
        return AnthropicLlmProvider()
    return MockLlmProvider()
