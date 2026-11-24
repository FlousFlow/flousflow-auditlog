# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo import api, models

from odoo.addons.flousflow_auditlog.models.operation_scope import audit_document_operation


class AuditAttachmentRule(models.Model):
    _inherit = "auditlog.attachment.rule"

    @api.model
    def _supported_points(self):
        return super()._supported_points() | {("purchase.order", "confirm")}


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        with audit_document_operation(self, self.env._("Confirm purchase order")):
            return super().button_confirm()

    def button_approve(self, force=False):
        with audit_document_operation(self, self.env._("Approve purchase order")):
            return super().button_approve(force=force)

    def write(self, vals):
        # Check actual resulting values, including a simultaneous change of
        # journal/company/domain fields. Exceptions roll back the transaction.
        transitioning = self.filtered(lambda rec: rec.state != "purchase") if vals.get("state") == "purchase" else self.browse()
        if not transitioning:
            return super().write(vals)
        with audit_document_operation(self, self.env._("Confirm purchase order")):
            result = super().write(vals)
            completed = transitioning.filtered(lambda rec: rec.state == "purchase")
            self.env["auditlog.attachment.rule"]._check_attachments(completed, "confirm", capture=True)
            return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        completed = records.filtered(lambda rec: rec.state == "purchase")
        if completed:
            self.env["auditlog.attachment.rule"]._check_attachments(completed, "confirm", capture=True)
        return records
