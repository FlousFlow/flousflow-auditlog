# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo import api, models

from odoo.addons.flousflow_auditlog.models.operation_scope import audit_operation


class AuditAttachmentRule(models.Model):
    _inherit = "auditlog.attachment.rule"

    @api.model
    def _supported_points(self):
        return super()._supported_points() | {("sale.order", "confirm")}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        with audit_operation(self.env._("Confirm sales order")):
            return super().action_confirm()

    def write(self, vals):
        # Check actual resulting values, including a simultaneous change of
        # journal/company/domain fields. Exceptions roll back the transaction.
        transitioning = self.filtered(lambda rec: rec.state != "sale") if vals.get("state") == "sale" else self.browse()
        if not transitioning:
            return super().write(vals)
        with audit_operation(self.env._("Confirm sales order")):
            result = super().write(vals)
            completed = transitioning.filtered(lambda rec: rec.state == "sale")
            self.env["auditlog.attachment.rule"]._check_attachments(completed, "confirm")
            return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        completed = records.filtered(lambda rec: rec.state == "sale")
        if completed:
            self.env["auditlog.attachment.rule"]._check_attachments(completed, "confirm")
        return records
