import pytest

from app.epc import (
    decode_epc,
    detect_epc_scheme,
    epc_scheme_is_allowed,
    normalize_epc,
    parse_epc,
    sscc96_with_check_digit,
    sscc96_without_check_digit,
)


def test_normalize_epc_uppercases_without_losing_leading_zeroes() -> None:
    assert normalize_epc(" 0x00a1b2 ") == "00A1B2"


def test_parse_epc_uses_unsigned_arbitrary_precision_integer() -> None:
    epc = parse_epc("31D55BE6800002156C000000")

    assert epc.hex_value == "31D55BE6800002156C000000"
    assert epc.decimal_value == str(int("31D55BE6800002156C000000", 16))
    assert epc.bit_length == 96


def test_epc_scheme_detection_supports_multiple_gs1_schemes() -> None:
    assert detect_epc_scheme("31D55CD1D800000001000000") == "SSCC-96"
    assert detect_epc_scheme("300000000000000000000000") == "SGTIN-96"
    assert epc_scheme_is_allowed("31D55CD1D800000001000000", ["SSCC-96"])
    assert not epc_scheme_is_allowed("31D55CD1D800000001000000", ["SGTIN-96"])


def test_sscc96_returns_payload_without_check_digit() -> None:
    assert sscc96_without_check_digit("310000000000000000000000") == "0000"
    assert sscc96_without_check_digit("31D55CD1D800000001000000") == "000000001"
    assert sscc96_without_check_digit("31D55CD1D80000000A000000") == "000000010"
    assert sscc96_without_check_digit("300000000000000000000001") is None


def test_decode_epc_returns_sscc96_serial_or_none_for_unknown_formats() -> None:
    assert sscc96_with_check_digit("31D55CD1D800000001000000") == "057150620000000015"
    assert sscc96_with_check_digit("31D55CD1D80000000A000000") == "057150620000000107"
    assert decode_epc("31D55CD1D800000001000000") == "SSCC-96: 057150620000000015"
    assert decode_epc("00112233445566778899AABB") is None


@pytest.mark.parametrize("value", ["", "ABC", "GG", "0x"])
def test_normalize_epc_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_epc(value)