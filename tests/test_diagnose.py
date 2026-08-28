from dtc_log_intelligence.diagnosis.diagnose import _extract_json


def test_extracts_clean_json():
    assert _extract_json('{"root_cause": "healthy", "confidence": 0.9}') == {
        "root_cause": "healthy", "confidence": 0.9,
    }


def test_extracts_json_wrapped_in_markdown_fences():
    raw = '```json\n{"root_cause": "healthy", "confidence": 0.9}\n```'
    assert _extract_json(raw) == {"root_cause": "healthy", "confidence": 0.9}


def test_extracts_json_with_leading_prose():
    raw = 'Here is my analysis:\n{"root_cause": "network_dropout", "confidence": 0.8}\nHope that helps!'
    assert _extract_json(raw) == {"root_cause": "network_dropout", "confidence": 0.8}


def test_returns_none_for_non_json_response():
    assert _extract_json("I'm not sure what's wrong with this vehicle.") is None


def test_returns_none_for_malformed_json():
    assert _extract_json('{"root_cause": "healthy",}') is None
