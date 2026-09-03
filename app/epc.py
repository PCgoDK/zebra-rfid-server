from dataclasses import dataclass


EPC_SCHEMES = {
    "SSCC-96": 0x31,
    "SGTIN-96": 0x30,
    "SGLN-96": 0x32,
    "GRAI-96": 0x33,
    "GIAI-96": 0x34,
    "GSRN-96": 0x2D,
    "GSRNP-96": 0x2E,
    "GDTI-96": 0x2C,
    "CPI-96": 0x3C,
    "GCN-96": 0x3F,
    "ITIP-110": 0x40,
    "ITIP-212": 0x41,
}


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


def detect_epc_scheme(value: str) -> str | None:
    epc = normalize_epc(value)
    if len(epc) < 2:
        return None
    header = int(epc[:2], 16)
    return next((scheme for scheme, scheme_header in EPC_SCHEMES.items() if header == scheme_header), None)


def epc_scheme_is_allowed(value: str, allowed_schemes: list[str] | None) -> bool:
    return allowed_schemes is None or detect_epc_scheme(value) in allowed_schemes


def sscc96_without_check_digit(value: str) -> str | None:
    """Return the SSCC serial reference without its extension/check digit."""
    epc = normalize_epc(value)
    if len(epc) != 24 or not epc.startswith("31"):
        return None
    partition = (int(epc, 16) >> 82) & 0b111
    partitions = {
        0: (40, 12, 18, 5),
        1: (37, 11, 21, 6),
        2: (34, 10, 24, 7),
        3: (30, 9, 28, 8),
        4: (27, 8, 31, 9),
        5: (24, 7, 34, 10),
        6: (20, 6, 38, 11),
    }
    if partition not in partitions:
        return None
    company_bits, company_digits, serial_bits, serial_digits = partitions[partition]
    payload = (int(epc, 16) >> 24) & ((1 << 58) - 1)
    company_prefix = payload >> serial_bits
    serial_reference = payload & ((1 << serial_bits) - 1)
    serial = f"{serial_reference:0{serial_digits}d}"
    return serial[1:]


def sscc96_with_check_digit(value: str) -> str | None:
    epc = normalize_epc(value)
    if len(epc) != 24 or not epc.startswith("31"):
        return None
    partition = (int(epc, 16) >> 82) & 0b111
    partitions = {
        0: (40, 12, 18, 5),
        1: (37, 11, 21, 6),
        2: (34, 10, 24, 7),
        3: (30, 9, 28, 8),
        4: (27, 8, 31, 9),
        5: (24, 7, 34, 10),
        6: (20, 6, 38, 11),
    }
    if partition not in partitions:
        return None
    _, company_digits, serial_bits, serial_digits = partitions[partition]
    payload = (int(epc, 16) >> 24) & ((1 << 58) - 1)
    company_prefix = payload >> serial_bits
    serial_reference = payload & ((1 << serial_bits) - 1)
    serial = f"{serial_reference:0{serial_digits}d}"
    sscc_without_check_digit = serial[0] + f"{company_prefix:0{company_digits}d}" + serial[1:]
    weighted_sum = sum(
        int(digit) * (3 if position % 2 == 0 else 1)
        for position, digit in enumerate(reversed(sscc_without_check_digit))
    )
    return f"{sscc_without_check_digit}{(10 - weighted_sum % 10) % 10}"


def decode_epc(value: str) -> str | None:
    sscc = sscc96_with_check_digit(value)
    if sscc is not None:
        return f"SSCC-96: {sscc}"
    return None