from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.domain.money import Paise, format_paise, rupees_to_paise


class Amount(BaseModel):
    value: Paise


def test_paise_accepts_integers():
    assert Amount(value=499900).value == 499900


@pytest.mark.parametrize("bad", [4999.0, 4999.5, "499900", Decimal("499900")])
def test_paise_rejects_anything_that_is_not_an_int(bad):
    """Strict typing is the point: 4999.0 looks harmless but means someone is
    doing rupee arithmetic in floats somewhere upstream."""
    with pytest.raises(ValidationError):
        Amount(value=bad)


def test_paise_rejects_negative():
    with pytest.raises(ValidationError):
        Amount(value=-1)


def test_rupees_to_paise_refuses_floats():
    with pytest.raises(TypeError):
        rupees_to_paise(4999.0)


@pytest.mark.parametrize(
    ("rupees", "paise"),
    [("4999", 499900), ("4999.00", 499900), (Decimal("14997.50"), 1499750), (1, 100)],
)
def test_rupees_to_paise(rupees, paise):
    assert rupees_to_paise(rupees) == paise


def test_rupees_to_paise_rejects_sub_paise_precision():
    with pytest.raises(ValueError):
        rupees_to_paise("10.001")


@pytest.mark.parametrize(
    ("paise", "display"),
    [
        (499900, "₹4,999.00"),
        (1499700, "₹14,997.00"),
        (100000000, "₹10,00,000.00"),
        (50, "₹0.50"),
        (0, "₹0.00"),
    ],
)
def test_format_paise_uses_indian_grouping(paise, display):
    assert format_paise(paise) == display
