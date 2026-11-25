# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import BinaryBytes

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountAttachmentControl(AccountTestInvoicingCommon):
    """Regression coverage for invoice and journal-entry enforcement."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rule_model = cls.env["auditlog.attachment.rule"]
        cls.move_model = cls.env["account.move"]

    def _create_rule(self, move_type):
        return self.rule_model.create({
            "name": "Required %s evidence" % move_type,
            "active": True,
            "company_id": self.env.company.id,
            "model_id": self.env["ir.model"]._get("account.move").id,
            "stage": "post",
            "domain_text": repr([("move_type", "=", move_type)]),
            "minimum_count": 1,
        })

    def _create_invoice(self):
        return self.move_model.create({
            "move_type": "out_invoice",
            "journal_id": self.company_data["default_journal_sale"].id,
            "partner_id": self.partner_a.id,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "quantity": 1,
                "price_unit": 10,
                "tax_ids": [],
            })],
        })

    def _create_entry(self):
        return self.move_model.create({
            "move_type": "entry",
            "journal_id": self.company_data["default_journal_misc"].id,
            "line_ids": [
                Command.create({
                    "account_id": self.company_data["default_account_expense"].id,
                    "debit": 10,
                    "credit": 0,
                }),
                Command.create({
                    "account_id": self.company_data["default_account_revenue"].id,
                    "debit": 0,
                    "credit": 10,
                }),
            ],
        })

    def _add_evidence(self, move):
        return self.env["ir.attachment"].create({
            "name": "supporting-document.txt",
            "res_model": move._name,
            "res_id": move.id,
            "raw": BinaryBytes(b"accounting evidence"),
            "ff_audit_evidence": True,
        })

    def test_contextual_rule_form_separates_invoice_and_entry_domains(self):
        invoice_action = self.rule_model.open_contextual_rules(
            "account.move", False, "out_invoice", False, False, True
        )
        entry_action = self.rule_model.open_contextual_rules(
            "account.move", False, "entry", False, False, True
        )
        self.assertEqual(invoice_action["view_mode"], "form")
        self.assertEqual(entry_action["view_mode"], "form")
        self.assertTrue(invoice_action["context"]["default_active"])
        self.assertTrue(entry_action["context"]["default_active"])
        self.assertEqual(
            invoice_action["context"]["default_domain_text"],
            repr([("move_type", "=", "out_invoice")]),
        )
        self.assertEqual(
            entry_action["context"]["default_domain_text"],
            repr([("move_type", "=", "entry")]),
        )

    def test_invoice_post_requires_and_accepts_designated_evidence(self):
        rule = self._create_rule("out_invoice")
        invoice = self._create_invoice()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            invoice.action_post()
        self.assertEqual(invoice.state, "draft")
        self._add_evidence(invoice)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertTrue(rule)

    def test_journal_entry_post_requires_and_accepts_designated_evidence(self):
        self._create_rule("entry")
        entry = self._create_entry()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            entry.action_post()
        self.assertEqual(entry.state, "draft")
        self._add_evidence(entry)
        entry.action_post()
        self.assertEqual(entry.state, "posted")

    def test_supported_points_include_accounting_models(self):
        points = self.rule_model._supported_points()
        self.assertIn(("account.move", "post"), points)
        self.assertIn(("account.payment", "post"), points)
