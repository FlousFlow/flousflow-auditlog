# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from base64 import b64encode

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSaleAttachmentControl(TransactionCase):
    def test_rule_rejects_missing_and_accepts_distinct_evidence(self):
        partner = self.env["res.partner"].create({"name": "Audit test customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        rule = self.env["auditlog.attachment.rule"].create({
            "name": "Evidence required", "active": True,
            "company_id": order.company_id.id,
            "model_id": self.env["ir.model"]._get("sale.order").id,
            "stage": "confirm", "minimum_count": 1,
        })
        with self.assertRaises(UserError):
            rule._check_attachments(order, "confirm")
        attachment = self.env["ir.attachment"].create({
            "name": "support.txt", "res_model": order._name, "res_id": order.id,
            "datas": b64encode(b"evidence"),
        })
        with self.assertRaises(UserError):
            rule._check_attachments(order, "confirm")
        attachment.ff_audit_evidence = True
        rule._check_attachments(order, "confirm")
