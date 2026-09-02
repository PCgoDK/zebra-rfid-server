from dataclasses import dataclass


@dataclass(frozen=True)
class EpcValue:
    hex_value: str
    decimal_value: str
    bit_length: int


def normalize_epc(value: str) -> str:
    normalized = value.strip().replace(" ", "").upper()
    if normalized.startswith("0X"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("EPC must not be empty")
    if len(normalized) % 2:
        raise ValueError("EPC must contain a whole number of bytes")
    if any(character not in "0123456789ABCDEF" for character in normalized):
        raise ValueError("EPC must be hexadecimal")
    return normalized


def parse_epc(value: str) -> EpcValue:
    hex_value = normalize_epc(value)
    return EpcValue(
        hex_value=hex_value,
        decimal_value=str(int(hex_value, 16)),
        bit_length=len(hex_value) * 4,
    )