# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo.tests.common import TransactionCase

from ..models.operation_scope import audit_operation


class TestBusinessActivity(TransactionCase):
    def test_one_row_per_operation_and_no_time_based_merge(self):
        logs = self.env["auditlog.log"].sudo()
        model = self.env["ir.model"]._get("res.partner")
        vals = {"model_id": model.id, "name": "Test document",
                "user_id": self.env.uid, "res_id": 123, "method": "write"}
        with audit_operation("First activity") as first:
            a = logs.create(vals.copy())
            b = logs.create(vals.copy())
        with audit_operation("First activity") as second:
            c = logs.create(vals.copy())
        logs.flush_model()
        activity = self.env["auditlog.activity"].sudo()
        rows = activity.search([("activity_key", "in", [first, second])])
        self.assertEqual(len(rows), 2)
        group = rows.filtered(lambda row: row.activity_key == first)
        self.assertEqual(group.event_count, 2)
        self.assertEqual(group.record_count, 1)
        self.assertEqual(group.name, "First activity")
        self.assertEqual(set(logs.search(group.action_open_events()["domain"]).ids), {a.id, b.id})
        self.assertNotIn(c.id, logs.search(group.action_open_events()["domain"]).ids)

    def test_unrelated_background_logs_stay_separate(self):
        logs = self.env["auditlog.log"].sudo()
        vals = {"model_id": self.env["ir.model"]._get("res.partner").id,
                "name": "Test", "res_id": 123, "method": "write"}
        a, b = logs.create([vals.copy(), vals.copy()])
        logs.flush_model()
        self.assertNotEqual(a.activity_key, b.activity_key)
        rows = self.env["auditlog.activity"].sudo().search([
            ("activity_key", "in", [a.activity_key, b.activity_key])
        ])
        self.assertEqual(len(rows), 2)
