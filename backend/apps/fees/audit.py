"""Audit hook extension point for fees workflows."""


def record_audit_event(action: str, *, actor, obj, details: dict | None = None) -> None:
    """Deliberate no-op extension point; the dedicated audit app arrives in a later phase."""
    return None
