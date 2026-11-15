import pytest

from lib.ceo_text import TooLong, check_ceo_text, trim_ceo_text


def test_legacy_refuses_long_text():
    with pytest.raises(TooLong):
        check_ceo_text({"why": "x" * 91})
    with pytest.raises(TooLong):
        check_ceo_text({"why": "\n".join(["line"] * 6)})


def test_trim_shared_line_budget():
    result = trim_ceo_text({"why": "\n".join(["x" * 100] * 4), "expected": "one\ntwo"})
    assert result == {"why": "\n".join(["x" * 89 + "…"] * 4), "expected": "one…"}
    check_ceo_text(result)


def test_trim_unchanged_short_text():
    assert trim_ceo_text({"why": "Ready", "expected": None}) == {"why": "Ready"}
