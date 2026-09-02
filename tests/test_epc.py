import pytest

from app.epc import normalize_epc, parse_epc


def test_normalize_epc_uppercases_without_losing_leading_zeroes() -> None:
    assert normalize_epc(" 0x00a1b2 ") == "00A1B2"


def test_parse_epc_uses_unsigned_arbitrary_precision_integer() -> None:
    epc = parse_epc("31D55BE6800002156C000000")

    assert epc.hex_value == "31D55BE6800002156C000000"
    assert epc.decimal_value == str(int("31D55BE6800002156C000000", 16))
    assert epc.bit_length == 96


@pytest.mark.parametrize("value", ["", "ABC", "GG", "0x"])
def test_normalize_epc_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_epc(value)