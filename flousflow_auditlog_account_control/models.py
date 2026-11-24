# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo import api, models

from odoo.addons.flousflow_auditlog.models.operation_scope import audit_operation


class AuditAttachmentRule(models.Model):
    _inherit = "auditlog.attachment.rule"

    @api.model
    def _supported_points(self):
        return super()._supported_points() | {("account.move", "post")}


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        with audit_operation(self.env._("Post accounting document")):
            return super()._post(soft=soft)

    def write(self, vals):
        # Check actual resulting values, including a simultaneous change of
        # journal/company/domain fields. Exceptions roll back the transaction.
        transitioning = self.filtered(lambda rec: rec.state != "posted") if vals.get("state") == "posted" else self.browse()
        if not transitioning:
            return super().write(vals)
        with audit_operation(self.env._("Post accounting document")):
            result = super().write(vals)
            completed = transitioning.filtered(lambda rec: rec.state == "posted")
            self.env["auditlog.attachment.rule"]._check_attachments(completed, "post", capture=True)
            return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        completed = records.filtered(lambda rec: rec.state == "posted")
        if completed:
            self.env["auditlog.attachment.rule"]._check_attachments(completed, "post", capture=True)
        return records
