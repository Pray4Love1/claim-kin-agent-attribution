from hyperliquid.utils.f303_helpers import format_withdrawable


def test_format_withdrawable_integer():
    assert format_withdrawable("1000") == "Withdrawable: 1000"


def test_format_withdrawable_trim_trailing_zeroes():
    assert format_withdrawable("1234.5000") == "Withdrawable: 1234.5"


def test_format_withdrawable_small_decimal():
    assert format_withdrawable("0.0001000") == "Withdrawable: 0.0001"
