from src.utils.coordinate import is_valid_coordinate


def test_valid_coordinate_tuple() -> None:
    assert is_valid_coordinate((100, 200, 7)) is True


def test_valid_coordinate_list() -> None:
    assert is_valid_coordinate([100, 200, 7]) is True


def test_valid_coordinate_with_extra_elements() -> None:
    assert is_valid_coordinate((100, 200, 7, 999, 'extra')) is True


def test_invalid_coordinate_none() -> None:
    assert is_valid_coordinate(None) is False


def test_invalid_coordinate_empty_list() -> None:
    assert is_valid_coordinate([]) is False


def test_invalid_coordinate_too_short() -> None:
    assert is_valid_coordinate([100, 200]) is False


def test_invalid_coordinate_with_none_x() -> None:
    assert is_valid_coordinate((None, 200, 7)) is False


def test_invalid_coordinate_with_none_y() -> None:
    assert is_valid_coordinate((100, None, 7)) is False


def test_invalid_coordinate_with_none_z() -> None:
    assert is_valid_coordinate((100, 200, None)) is False


def test_invalid_coordinate_wrong_type() -> None:
    assert is_valid_coordinate("100,200,7") is False


def test_invalid_coordinate_dict() -> None:
    assert is_valid_coordinate({'x': 100, 'y': 200, 'z': 7}) is False


def test_valid_coordinate_with_floats() -> None:
    # Floats are valid (will be converted to int later)
    assert is_valid_coordinate((100.5, 200.3, 7.0)) is True


def test_valid_coordinate_with_strings() -> None:
    # Strings are technically "not None", validation passes
    # (conversion to int happens later in calling code)
    assert is_valid_coordinate(("100", "200", "7")) is True


def test_invalid_coordinate_single_value() -> None:
    assert is_valid_coordinate(123) is False


def test_valid_coordinate_zero_values() -> None:
    assert is_valid_coordinate((0, 0, 0)) is True


def test_valid_coordinate_negative_values() -> None:
    assert is_valid_coordinate((-100, -200, 7)) is True


def test_invalid_coordinate_mixed_none() -> None:
    assert is_valid_coordinate((100, None, None)) is False


def test_logging_option_does_not_crash() -> None:
    # Test that log_invalid flag doesn't cause errors
    assert is_valid_coordinate(None, log_invalid=True, label="test") is False
    assert is_valid_coordinate((100, 200, 7), log_invalid=True, label="test") is True
