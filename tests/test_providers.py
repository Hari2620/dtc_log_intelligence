import json

from dtc_log_intelligence.diagnosis.providers import MockLlmProvider


def test_mock_provider_returns_valid_json():
    provider = MockLlmProvider()
    raw = provider.complete("DTC codes observed this session:\n  P0301: seen confirmed 5x")
    parsed = json.loads(raw)
    assert parsed["root_cause"] == "misfire_cascade"


def test_mock_provider_defaults_to_healthy_with_no_codes():
    provider = MockLlmProvider()
    parsed = json.loads(provider.complete("DTC codes observed this session:\n  (none)"))
    assert parsed["root_cause"] == "healthy"


def test_mock_provider_ambiguous_on_shared_p0128_code():
    """The known limitation, made explicit as a test: the naive baseline always
    guesses cooling_failure for P0128, even on the sensor-drift sessions that
    also emit it. This isn't a bug -- it's the documented gap a real LLM is
    supposed to close (see README)."""
    provider = MockLlmProvider()
    parsed = json.loads(provider.complete("DTC codes observed this session:\n  P0128: seen confirmed 3x"))
    assert parsed["root_cause"] == "cooling_failure"
