"""Custom exceptions for the append-only ledger app."""


class LedgerImmutableError(Exception):
    """Raised when code attempts to modify, update, or delete a ledger entry."""

    @classmethod
    def for_operation(cls, operation: str) -> "LedgerImmutableError":
        """Build a consistent append-only error message for the blocked operation."""
        return cls(f"Ledger entries are append-only; '{operation}' is not allowed.")
