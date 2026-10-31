import pytest

from medixio.shared import capitalize


@pytest.mark.parametrize(
    ("param", "expected"),
    [("python", "Python"), ("pYTHON", "Python"), ("PyTHon", "Python")],
    ids=["lowercase", "first_lower_rest_upper", "mixed_case"],
)
def test_capitalize(param, expected):
    assert capitalize(param) == expected
