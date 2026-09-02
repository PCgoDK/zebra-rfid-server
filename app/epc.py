"""EPC normalization and integer conversion."""

import re


_HEX = re.compile(r"^[0-9A-F]+$")


def normalize_epc(value: str) -> str:
    """Normalize an EPC hexadecimal value while preserving leading zeroes."""
    normalized = value.strip().upper()
    if normalized.startswith("0X"):
        normalized = normalized[2:]
    if not normalized or len(normalized) % 2 or not _HEX.fullmatch(normalized):
        raise ValueError("EPC must be a non-empty, even-length hexadecimal value")
    return normalized


def epc_to_decimal(epc_hex: str) -> str:
    """Convert an EPC value to an arbitrary-precision unsigned decimal string."""
    return str(int(normalize_epc(epc_hex), 16))


def epc_bit_length(epc_hex: str) -> int:
    """Return the encoded EPC bit length, including leading zeroes."""
    return len(normalize_epc(epc_hex)) * 4
