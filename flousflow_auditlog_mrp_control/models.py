# License AGPL-3.0 or later.
from odoo import api, models
from odoo.addons.flousflow_auditlog.models.operation_scope import audit_operation


class AuditAttachmentRule(models.Model):
    _inherit = "auditlog.attachment.rule"

    @api.model
    def _supported_points(self):
        return super()._supported_points() | {("mrp.production", "confirm"), ("mrp.production", "complete"), ("mrp.unbuild", "complete")}


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def action_confirm(self):
        pending = self.filtered(lambda rec: rec.state == "draft")
        with audit_operation(self.env._("Confirm manufacturing order")):
            result = super().action_confirm()
            self.env["auditlog.attachment.rule"]._check_attachments(
                pending.filtered(lambda rec: rec.state not in ("draft", "cancel")),
                "confirm", capture=True
            )
            return result

    def button_mark_done(self):
        pending = self.filtered(lambda rec: rec.state not in ("done", "cancel"))
        with audit_operation(self.env._("Complete manufacturing order")):
            result = super().button_mark_done()
            self.env["auditlog.attachment.rule"]._check_attachments(
                pending.filtered(lambda rec: rec.state == "done"), "complete", capture=True
            )
            return result


class MrpUnbuild(models.Model):
    _inherit = "mrp.unbuild"

    def action_unbuild(self):
        pending = self.filtered(lambda rec: rec.state == "draft")
        with audit_operation(self.env._("Complete unbuild order")):
            result = super().action_unbuild()
            self.env["auditlog.attachment.rule"]._check_attachments(
                pending.filtered(lambda rec: rec.state == "done"), "complete", capture=True
            )
            return result
