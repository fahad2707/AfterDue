"""Seed-stable synthetic identities.

Persistence IDs (`run_id`, `customer_id`, `case_id`) stay unique per generate
so Mongo isolation is preserved. These keys are derived only from the
population index and halt ordinal, so two worlds drawn from the same
SimulationConfig + seed share the same simulation identity even when their
database IDs differ.
"""


def synthetic_customer_key(index: int) -> str:
    return f"subscriber_{index:04d}"


def synthetic_case_key(index: int, halt_ordinal: int) -> str:
    """`halt_ordinal` is 1-based: first closed halt episode is 01."""
    return f"{synthetic_customer_key(index)}_halt_{halt_ordinal:02d}"


def halt_ordinal_from_episode_id(episode_id: str) -> int:
    """Episode ids are `he_1`, `he_2`, … — assigned in halt order."""
    prefix, _, rest = episode_id.partition("_")
    if prefix != "he" or not rest.isdigit():
        raise ValueError(f"unrecognised halt episode id {episode_id!r}")
    return int(rest)
