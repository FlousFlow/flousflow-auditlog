# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAlwaysOnAudit(TransactionCase):
    """The user-facing audit contract is automatic, without opt-in rules."""

    def test_create_write_and_unlink_are_logged_without_rule(self):
        before = fields.Datetime.now()
        partner = self.env["res.partner"].create({"name": "Always-on audit test"})
        partner.write({"name": "Always-on audit test updated"})
        partner_id = partner.id
        partner.unlink()
        logs = self.env["auditlog.log"].sudo().search([
            ("model_model", "=", "res.partner"),
            ("res_id", "=", partner_id),
            ("create_date", ">=", before),
        ])
        self.assertEqual(set(logs.mapped("method")), {"create", "write", "unlink"})

    def test_write_log_contains_human_readable_before_and_after(self):
        partner = self.env["res.partner"].create({"name": "Before label"})
        partner.write({"name": "After label"})
        log = self.env["auditlog.log"].sudo().search([
            ("model_model", "=", "res.partner"),
            ("res_id", "=", partner.id),
            ("method", "=", "write"),
        ], order="id desc", limit=1)
        self.assertTrue(log)
        line = log.line_ids.filtered(lambda item: item.field_name == "name")
        self.assertTrue(line)
        self.assertEqual(line.old_value_text, "Before label")
        self.assertEqual(line.new_value_text, "After label")
