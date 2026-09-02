import pytest

from app.epc import epc_bit_length, epc_to_decimal, normalize_epc


def test_normalize_epc_preserves_leading_zeroes() -> None:
    assert normalize_epc(" 0x0031d55be6800002156c000000 ") == "0031D55BE6800002156C000000"


def test_epc_decimal_supports_values_larger_than_64_bits() -> None:
    epc = "31D55BE6800002156C000000"
    assert epc_to_decimal(epc) == str(int(epc, 16))
    assert epc_bit_length(epc) == 96


@pytest.mark.parametrize("value", ["", "ABC", "GG", "0x"])
def test_rejects_invalid_epc(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_epc(value)
