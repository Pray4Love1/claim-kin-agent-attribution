from examples.codex_runner_f303 import format_withdrawable

def test_format_withdrawable_strips_scientific_notation_for_whole_numbers():
    assert format_withdrawable("1000") == "Withdrawable: 1000"

def test_format_withdrawable_preserves_decimal_precision():
    assert format_withdrawable("1000.5000") == "Withdrawable: 1000.5"
    assert format_withdrawable("0.0001000") == "Withdrawable: 0.0001"

def test_format_withdrawable_handles_zero_values():
    assert format_withdrawable("0.0000") == "Withdrawable: 0"
