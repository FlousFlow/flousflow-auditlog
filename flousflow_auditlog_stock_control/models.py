# License AGPL-3.0 or later.
from odoo import api, models
from odoo.addons.flousflow_auditlog.models.operation_scope import audit_operation


class AuditAttachmentRule(models.Model):
    _inherit = "auditlog.attachment.rule"

    @api.model
    def _supported_points(self):
        return super()._supported_points() | {("stock.picking", "complete")}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        pending = self.filtered(lambda rec: rec.state not in ("done", "cancel"))
        with audit_operation(self.env._("Validate inventory transfer")):
            result = super()._action_done()
            self.env["auditlog.attachment.rule"]._check_attachments(
                pending.filtered(lambda rec: rec.state == "done"), "complete", capture=True
            )
            return result
