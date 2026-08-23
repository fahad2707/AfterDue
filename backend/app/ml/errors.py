class FeatureSchemaMismatch(RuntimeError):
    """Current feature schema does not match the saved artifact."""


class ModelUnavailable(RuntimeError):
    """RECLAIM was requested but no valid active artifact exists."""
