from dtc_log_intelligence.parser.common import LineParseError, tokenize_line
from dtc_log_intelligence.parser.dtc_parser import parse_dtc_lines
from dtc_log_intelligence.parser.uds_parser import parse_uds_lines


def test_tokenize_line_extracts_timestamp_and_tokens():
    ts, tokens = tokenize_line("[2026-08-28T09:00:00.000Z] ECU=0x7E0 DTC=P0301 STATUS=0x08")
    assert ts == "2026-08-28T09:00:00.000Z"
    assert tokens == {"ECU": "0x7E0", "DTC": "P0301", "STATUS": "0x08"}


def test_tokenize_line_rejects_missing_bracket():
    import pytest
    with pytest.raises(LineParseError):
        tokenize_line("ECU=0x7E0 DTC=P0301 STATUS=0x08")


def test_dtc_none_line_produces_no_record():
    result = parse_dtc_lines(["[2026-08-28T09:00:00.000Z] ECU=0x7E0 DTC=NONE STATUS=0x00"], "s1")
    assert result.records == []
    assert result.warnings == []


def test_dtc_line_with_full_freeze_frame():
    line = ("[2026-08-28T09:00:00.000Z] ECU=0x7E0 DTC=P0301 STATUS=0x08 "
            "RPM=850.0 COOLANT_C=91.0 TPS_PCT=12.0 LOAD_PCT=35.0 MAF_GS=6.0 STFT_PCT=-1.0")
    result = parse_dtc_lines([line], "s1")
    assert len(result.records) == 1
    record = result.records[0]
    assert record.code == "P0301"
    assert record.confirmed is True
    assert record.pending is False
    assert record.freeze_frame.rpm == 850.0
    assert record.freeze_frame.coolant_temp_c == 91.0


def test_dtc_line_with_missing_freeze_frame_fields():
    result = parse_dtc_lines(["[2026-08-28T09:00:00.000Z] ECU=0x7E0 DTC=U0100 STATUS=0x04"], "s1")
    record = result.records[0]
    assert record.pending is True
    assert record.freeze_frame.rpm is None


def test_malformed_dtc_line_produces_warning_not_crash():
    result = parse_dtc_lines(["this is not a valid line", "[ts] DTC=P0301 STATUS=zz"], "s1")
    assert result.records == []
    assert len(result.warnings) == 2


def test_uds_positive_response_parsed():
    result = parse_uds_lines(
        ["[ts] DIR=RX ECU=0x7E8 SID=0x59 SUB=0x02 DATA=0803010800000000"], "s1"
    )
    frame = result.frames[0]
    assert frame.service_id == "0x59"
    assert frame.sub_function == "0x02"
    assert frame.nrc is None


def test_uds_negative_response_parsed():
    result = parse_uds_lines(["[ts] DIR=RX ECU=0x7E8 SID=0x7F REQ_SID=0x19 NRC=0x11"], "s1")
    frame = result.frames[0]
    assert frame.service_id == "0x19"
    assert frame.nrc == "0x11"


def test_uds_timeout_parsed_as_synthetic_nrc():
    result = parse_uds_lines(["[ts] DIR=RX ECU=0x7E8 TIMEOUT=1"], "s1")
    frame = result.frames[0]
    assert frame.nrc == "timeout"
