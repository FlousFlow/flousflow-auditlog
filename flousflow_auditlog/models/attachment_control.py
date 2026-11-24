# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class AuditAttachmentRule(models.Model):
    _name = "auditlog.attachment.rule"
    _description = "Attachment Control Rule"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=False)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True
    )
    model_id = fields.Many2one("ir.model", required=True, ondelete="restrict")
    stage = fields.Selection(
        [("confirm", "Confirmation"), ("post", "Posting"),
         ("complete", "Completion")], required=True, default="confirm"
    )
    domain_text = fields.Char(default="[]", required=True)
    minimum_count = fields.Integer(default=1, required=True)
    user_ids = fields.Many2many("res.users", string="Applicable users")
    group_ids = fields.Many2many("res.groups", string="Applicable groups")

    @api.model
    def _supported_points(self):
        # Optional technical adapters extend this list only when installed.
        return set()

    @api.constrains("minimum_count", "model_id", "stage", "active", "domain_text")
    def _check_rule(self):
        for rule in self:
            if rule.minimum_count < 1:
                raise ValidationError(self.env._("At least one attachment is required."))
            try:
                domain = literal_eval(rule.domain_text)
                if not isinstance(domain, list):
                    raise ValueError()
                self.env[rule.model_id.model].sudo().search(domain, limit=1)
            except (ValueError, TypeError, SyntaxError, KeyError, AssertionError) as exc:
                raise ValidationError(self.env._("Invalid rule domain.")) from exc
            if rule.active and (rule.model_id.model, rule.stage) not in self._supported_points():
                raise ValidationError(self.env._("No installed enforcement adapter for this operation."))

    @api.model
    def _check_attachments(self, records, stage):
        """Called from an installed server-side lifecycle adapter."""
        if not records:
            return
        if (records._name, stage) not in self._supported_points():
            raise UserError(self.env._("Unsupported attachment enforcement point."))
        rules = self.sudo().search([
            ("active", "=", True), ("model_id.model", "=", records._name),
            ("stage", "=", stage),
        ])
        if not rules:
            return
        actor = self.env.user
        groups = actor.sudo().all_group_ids if "all_group_ids" in actor._fields else actor.sudo().group_ids
        for record in records:
            applicable = rules.filtered(lambda rule:
                rule.company_id == record.company_id
                and (not rule.user_ids or actor in rule.user_ids)
                and (not rule.group_ids or bool(rule.group_ids & groups))
            )
            for rule in applicable:
                if not record.sudo().filtered_domain(literal_eval(rule.domain_text)):
                    continue
                # Explicitly designated evidence only. Do not mistake generated reports
                # or unrelated chatter files for supporting documentation.
                evidence = self.env["ir.attachment"].sudo().search([
                    ("res_model", "=", record._name), ("res_id", "=", record.id),
                    ("res_field", "=", False), ("type", "=", "binary"),
                    ("file_size", ">", 0), ("checksum", "!=", False),
                    ("ff_audit_evidence", "=", True),
                ])
                count = len(set(evidence.mapped("checksum")))
                if count < rule.minimum_count:
                    raise UserError(self.env._(
                        "%(document)s: %(rule)s requires %(required)s supporting file(s); %(actual)s found.",
                        document=record.display_name, rule=rule.name,
                        required=rule.minimum_count, actual=count,
                    ))


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    ff_audit_evidence = fields.Boolean(
        string="Supporting audit evidence", default=False, copy=False,
        help="Explicitly designated supporting document. Generated PDFs are not counted automatically.",
    )

    @api.constrains("ff_audit_evidence", "type", "file_size", "res_model", "res_id")
    def _check_audit_evidence(self):
        for att in self.filtered("ff_audit_evidence"):
            if att.type != "binary" or att.file_size <= 0 or not att.res_model or not att.res_id:
                raise ValidationError(self.env._("Supporting evidence must be a non-empty file linked to a document."))
