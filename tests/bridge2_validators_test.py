from scripts.list_bridge2_signers import (
    _abi_address,
    _decode_address_array,
    _decode_bool,
    _decode_uint,
)


def test_decode_address_array_round_trip():
    addresses = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
    ]
    # ABI-encoded dynamic address array: offset (0x20), length, two address words
    payload = (
        "0x"
        "0000000000000000000000000000000000000000000000000000000000000020"
        "0000000000000000000000000000000000000000000000000000000000000002"
        "0000000000000000000000001111111111111111111111111111111111111111"
        "0000000000000000000000002222222222222222222222222222222222222222"
    )
    assert _decode_address_array(payload) == addresses


def test_decode_uint_and_bool():
    assert _decode_uint("0x15") == 21
    assert _decode_bool("0x0") is False
    assert _decode_bool("0x1") is True


def test_abi_address_padding():
    stripped = "abcdef"
    encoded = _abi_address(stripped)
    assert encoded.endswith(stripped)
    assert len(encoded) == 64