# License AGPL-3.0 or later.
from odoo import api, models
from odoo.addons.flousflow_auditlog.models.operation_scope import audit_operation


class AuditAttachmentRule(models.Model):
    _inherit = "auditlog.attachment.rule"

    @api.model
    def _supported_points(self):
        return super()._supported_points() | {("stock.picking", "complete"), ("stock.quant", "complete"), ("stock.move", "complete")}


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


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _apply_inventory(self, date=None):
        with audit_operation(self.env._("Apply inventory adjustment")):
            pending = self.filtered(lambda quant: not (
                quant.env.context.get("from_inverse_qty")
                and quant.uom_id.compare(quant.inventory_diff_quantity, 0) == 0
            ))
            self.env["auditlog.attachment.rule"]._check_attachments(
                pending, "complete", capture=True
            )
            return super()._apply_inventory(date=date)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        pending = self.filtered(lambda move: move.is_scrap and move.state not in ("done", "cancel"))
        if not pending:
            return super()._action_done(cancel_backorder=cancel_backorder)
        with audit_operation(self.env._("Complete inventory scrap")):
            result = super()._action_done(cancel_backorder=cancel_backorder)
            self.env["auditlog.attachment.rule"]._check_attachments(
                pending.exists().filtered(lambda move: move.state == "done"),
                "complete", capture=True
            )
            return result
