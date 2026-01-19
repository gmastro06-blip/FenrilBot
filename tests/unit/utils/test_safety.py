from src.utils.safety import safe_int


def test_safe_int_none() -> None:
    assert safe_int(None) is None


def test_safe_int_string_number() -> None:
    assert safe_int("25") == 25


def test_safe_int_float() -> None:
    assert safe_int(45.0) == 45


def test_safe_int_invalid_string() -> None:
    assert safe_int("abc") is None


def test_safe_int_empty_string() -> None:
    assert safe_int("") is None
