# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo.tools import BinaryBytes
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
            "raw": BinaryBytes(b"evidence"),
        })
        with self.assertRaises(UserError):
            rule._check_attachments(order, "confirm")
        attachment.ff_audit_evidence = True
        rule._check_attachments(order, "confirm")

    def test_capture_protects_evidence_and_preserves_snapshot(self):
        partner = self.env["res.partner"].create({"name": "Evidence protection customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        rule = self.env["auditlog.attachment.rule"].create({
            "name": "Protected evidence", "active": True,
            "company_id": order.company_id.id,
            "model_id": self.env["ir.model"]._get("sale.order").id,
            "stage": "confirm", "minimum_count": 1, "protect_evidence": True,
        })
        attachment = self.env["ir.attachment"].create({
            "name": "support.txt", "res_model": order._name, "res_id": order.id,
            "raw": BinaryBytes(b"evidence"), "ff_audit_evidence": True,
        })
        rule._check_attachments(order, "confirm", capture=True)
        self.assertTrue(attachment.ff_audit_protected)
        snapshot = self.env["auditlog.attachment.compliance"].sudo().search([
            ("model_name", "=", order._name), ("resource_id", "=", order.id),
            ("rule_id", "=", rule.id),
        ])
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot.actual_count, 1)
        self.assertIn(attachment.checksum, snapshot.evidence_digest)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            attachment.unlink()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            attachment.write({"ff_audit_evidence": False})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            attachment.write({"raw": BinaryBytes(b"changed")})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            attachment.write({"ff_audit_protected": False})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            snapshot.write({"actual_count": 0})
        rule.active = False
        with self.assertRaises(UserError), self.env.cr.savepoint():
            attachment.unlink()

    def test_duplicate_files_do_not_meet_two_file_requirement(self):
        partner = self.env["res.partner"].create({"name": "Duplicate evidence customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        rule = self.env["auditlog.attachment.rule"].create({
            "name": "Two distinct documents", "active": True,
            "company_id": order.company_id.id,
            "model_id": self.env["ir.model"]._get("sale.order").id,
            "stage": "confirm", "minimum_count": 2,
        })
        for name in ("a.txt", "b.txt"):
            self.env["ir.attachment"].create({
                "name": name, "res_model": order._name, "res_id": order.id,
                "raw": BinaryBytes(b"same evidence"), "ff_audit_evidence": True,
            })
        with self.assertRaises(UserError), self.env.cr.savepoint():
            rule._check_attachments(order, "confirm", capture=True)

    def test_upload_wizard_creates_designated_evidence(self):
        partner = self.env["res.partner"].create({"name": "Evidence upload customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        wizard = self.env["auditlog.evidence.upload"].create({
            "model_name": order._name, "resource_id": order.id,
            "filename": "support.txt", "data": "c3VwcG9ydGluZyBkb2N1bWVudA==",
        })
        wizard.action_upload()
        att = self.env["ir.attachment"].search([
            ("res_model", "=", order._name), ("res_id", "=", order.id),
            ("ff_audit_evidence", "=", True),
        ])
        self.assertEqual(len(att), 1)
        self.assertEqual(att.company_id, order.company_id)

    def test_exception_is_single_use_and_revision_bound(self):
        from odoo import Command
        partner = self.env["res.partner"].create({"name": "Exception customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Exception actor", "login": "ff_exception_actor",
            "company_id": order.company_id.id,
            "company_ids": [Command.set([order.company_id.id])],
        })
        approver = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Exception approver", "login": "ff_exception_approver",
            "company_id": order.company_id.id,
            "company_ids": [Command.set([order.company_id.id])],
            "group_ids": [Command.set([
                self.env.ref("base.group_user").id,
                self.env.ref("sales_team.group_sale_manager").id,
                self.env.ref("flousflow_auditlog.group_attachment_exception").id,
            ])],
        })
        rule = self.env["auditlog.attachment.rule"].create({
            "name": "Exception enabled", "active": True, "allow_exception": True,
            "company_id": order.company_id.id,
            "model_id": self.env["ir.model"]._get("sale.order").id,
            "stage": "confirm", "minimum_count": 1,
        })
        grant = self.env["auditlog.attachment.exception"].with_user(approver).create({
            "rule_id": rule.id, "resource_id": order.id,
            "actor_id": actor.id, "reason": "Verified alternative evidence",
        })
        consumed = grant._consume(rule, order, actor)
        self.assertEqual(consumed.id, grant.id)
        self.assertFalse(grant._consume(rule, order, actor))
