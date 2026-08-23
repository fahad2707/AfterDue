"""Money in RECLAIM is always an integer number of paise.

₹4,999.00 is stored as 499900. There is no float anywhere in the money path:
floats cannot represent 0.01 exactly, and accumulated rounding error in a
system whose entire output is a rupee figure is not acceptable.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

#: Integer paise. `strict=True` rejects floats outright rather than silently
#: coercing 4999.5 or accepting 499900.0 as if it were well-typed.
Paise = Annotated[int, Field(strict=True, ge=0)]

PAISE_PER_RUPEE = 100


def rupees_to_paise(rupees: str | int | Decimal) -> int:
    """Convert a rupee amount to paise. Never accepts a float."""
    if isinstance(rupees, float):
        raise TypeError("refusing to convert float rupees; pass str, int or Decimal")
    amount = Decimal(str(rupees)) * PAISE_PER_RUPEE
    if amount != amount.to_integral_value():
        raise ValueError(f"{rupees} rupees is not a whole number of paise")
    return int(amount)


def format_paise(paise: int) -> str:
    """Render paise for display using Indian digit grouping: 1499700 -> ₹14,997.00."""
    if paise < 0:
        return "-" + format_paise(-paise)

    rupees, remainder = divmod(paise, PAISE_PER_RUPEE)
    digits = str(rupees)

    # Indian grouping: last three digits, then pairs (12,34,567).
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        grouped = ",".join([*parts, tail])
    else:
        grouped = digits

    return f"₹{grouped}.{remainder:02d}"
