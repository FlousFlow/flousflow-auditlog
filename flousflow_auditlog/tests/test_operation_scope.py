# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from unittest import TestCase

from ..models.operation_scope import audit_operation, current_operation


class TestOperationScope(TestCase):
    def test_nested_and_independent_operations(self):
        self.assertIsNone(current_operation())
        with audit_operation("Confirm SO") as first:
            with audit_operation("Create delivery") as nested:
                self.assertEqual(first, nested)
            self.assertEqual(current_operation(), first)
        with audit_operation("Confirm SO") as second:
            self.assertNotEqual(first, second)
        self.assertIsNone(current_operation())

    def test_exception_resets_scope(self):
        with self.assertRaises(ValueError):
            with audit_operation("Fail"):
                raise ValueError()
        self.assertIsNone(current_operation())
