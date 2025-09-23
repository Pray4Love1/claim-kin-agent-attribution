from examples.codex_runner_f303 import format_withdrawable


def test_format_withdrawable_preserves_integer_representation() -> None:
    assert format_withdrawable("1000") == "Withdrawable: 1000"
