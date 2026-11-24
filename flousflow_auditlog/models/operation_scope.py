# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_operation = ContextVar("flousflow_audit_operation", default=None)


def current_operation():
    return _operation.get()


@contextmanager
def audit_operation(label):
    """Correlate nested synchronous work, never trust caller RPC context."""
    existing = _operation.get()
    if existing is not None:
        yield existing
        return
    key = "%s [%s]" % (label, uuid4().hex)
    token = _operation.set(key)
    try:
        yield key
    finally:
        _operation.reset(token)
