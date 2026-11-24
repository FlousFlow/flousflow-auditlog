# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from ast import literal_eval
from datetime import timedelta
from uuid import uuid4

from odoo import api, fields, models, Command
from odoo.tools import SQL
from odoo.exceptions import ValidationError, UserError
from .operation_scope import current_operation


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
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    model_name = fields.Char(
        related="model_id.model", string="Technical Model Name", readonly=True
    )
    stage = fields.Selection(
        [("confirm", "Confirmation"), ("post", "Posting"),
         ("complete", "Completion")], required=True, default="confirm"
    )
    domain_text = fields.Char(default="[]", required=True)
    minimum_count = fields.Integer(default=1, required=True)
    revision = fields.Char(default=lambda self: uuid4().hex, readonly=True, copy=False)
    allow_exception = fields.Boolean(default=False)
    allowed_mimetypes = fields.Char(help="Comma-separated exact MIME types; blank permits any binary file.")
    protect_evidence = fields.Boolean(default=True, help="Preserve files used as evidence after completion.")
    user_ids = fields.Many2many("res.users", string="Applicable users")
    group_ids = fields.Many2many("res.groups", string="Applicable groups")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["revision"] = uuid4().hex
        return super().create(vals_list)

    def write(self, vals):
        return super().write(dict(vals, revision=uuid4().hex))

    @api.model
    def _supported_points(self):
        # Optional technical adapters extend this list only when installed.
        return set()

    @api.constrains("minimum_count", "model_id", "stage", "active", "domain_text")
    def _check_rule(self):
        for rule in self:
            if rule.minimum_count < 1:
                raise ValidationError(self.env._("At least one attachment is required."))
            if not any(point[0] == rule.model_id.model for point in self._supported_points()):
                raise ValidationError(self.env._("No installed enforcement adapter for this model."))
            try:
                domain = literal_eval(rule.domain_text)
                if not isinstance(domain, list):
                    raise ValueError()
                self.env[rule.model_id.model].search(domain, limit=1)
            except (ValueError, TypeError, SyntaxError, KeyError, AssertionError) as exc:
                raise ValidationError(self.env._("Invalid rule domain.")) from exc
            if rule.active and (rule.model_id.model, rule.stage) not in self._supported_points():
                raise ValidationError(self.env._("No installed enforcement adapter for this operation."))

    @api.model
    def open_contextual_rules(self, model_name, record_id=False, default_move_type=False, picking_type_id=False, payment_type=False):
        if not (
            self.env.user.has_group("flousflow_auditlog.group_document_control_manager")
            or self.env.user.has_group("base.group_system")
        ):
            raise UserError(self.env._("Only attachment control managers can configure rules."))
        points = sorted(point[1] for point in self._supported_points()
                        if point[0] == model_name)
        if not points:
            raise UserError(self.env._("This screen has no installed attachment enforcement adapter."))
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        defaults = {"default_model_id": model.id, "default_company_id": self.env.company.id,
                    "default_stage": points[0], "active_test": False}
        domain = [("model_id", "=", model.id), ("company_id", "=", self.env.company.id)]
        record = False
        if record_id:
            record = self.env[model_name].browse(int(record_id)).exists()
            if record:
                record.check_access("read")
                if record.company_id and record.company_id != self.env.company:
                    raise UserError(self.env._("Switch to the document company before configuring its rules."))
                if model_name == "account.move":
                    default_move_type = record.move_type
                elif model_name == "stock.picking":
                    picking_type_id = record.picking_type_id.id
                elif model_name == "account.payment":
                    payment_type = record.payment_type
        if model_name == "account.move" and default_move_type in {
            "entry", "out_invoice", "out_refund", "in_invoice", "in_refund",
            "out_receipt", "in_receipt",
        }:
            defaults["default_domain_text"] = repr([("move_type", "=", default_move_type)])
        if model_name == "stock.picking" and picking_type_id:
            picking_type = self.env["stock.picking.type"].browse(int(picking_type_id)).exists()
            if picking_type:
                picking_type.check_access("read")
                if picking_type.company_id == self.env.company:
                    defaults["default_domain_text"] = repr([("picking_type_id", "=", picking_type.id)])
        if model_name == "stock.move":
            if record_id and record and not record.is_scrap:
                raise UserError(self.env._("Only scrap moves are supported on this model."))
            defaults["default_domain_text"] = repr([("is_scrap", "=", True)])
        if model_name == "account.payment" and payment_type in {"inbound", "outbound"}:
            defaults["default_domain_text"] = repr([("payment_type", "=", payment_type)])
        action = self.env["ir.actions.actions"]._for_xml_id(
            "flousflow_auditlog.action_attachment_control"
        )
        action.update({"domain": domain, "context": defaults, "target": "current"})
        return action

    @api.model
    def open_evidence(self, model_name, record_ids):
        if not self.env.user.has_group("base.group_user"):
            raise UserError(self.env._("Internal users only."))
        if not any(point[0] == model_name for point in self._supported_points()):
            raise UserError(self.env._("Unsupported evidence document."))
        record = self.env[model_name].browse(record_ids).exists()
        record.ensure_one()
        record.check_access("write")
        if model_name == "stock.move" and not record.is_scrap:
            raise UserError(self.env._("Only scrap moves are supported on this model."))
        view = self.env.ref("flousflow_auditlog.view_evidence_upload_form")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Supporting documents"),
            "res_model": "auditlog.evidence.upload",
            "views": [(view.id, "form")],
            "context": {"default_model_name": model_name, "default_resource_id": record.id},
            "target": "new",
        }

    @api.model
    def _check_attachments(self, records, stage, capture=False):
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
                    ("company_id", "in", [False, record.company_id.id]),
                ])
                if capture and evidence:
                    evidence._ff_lock_evidence()
                    evidence.invalidate_recordset(["checksum", "file_size", "res_model", "res_id",
                                                   "res_field", "type", "ff_audit_evidence", "company_id", "mimetype"])
                    evidence = evidence.exists().filtered(lambda att:
                        att.res_model == record._name and att.res_id == record.id
                        and not att.res_field and att.type == "binary" and att.file_size > 0
                        and att.checksum and att.ff_audit_evidence
                        and (not att.company_id or att.company_id == record.company_id)
                    )
                allowed_mimes = {mime.strip().lower() for mime in (rule.allowed_mimetypes or "").split(",") if mime.strip()}
                if allowed_mimes:
                    evidence = evidence.filtered(lambda att: (att.mimetype or "").lower() in allowed_mimes)
                if record._name == "stock.quant":
                    previous = self.env["auditlog.attachment.compliance"].sudo().search([
                        ("model_name", "=", record._name), ("resource_id", "=", record.id),
                        ("stage", "=", stage), ("company_id", "=", record.company_id.id),
                        ("rule_id", "=", rule.id),
                    ])
                    used = {digest for row in previous for digest in (row.evidence_digest or "").splitlines()}
                    evidence = evidence.filtered(lambda att: att.checksum not in used)
                count = len(set(evidence.mapped("checksum")))
                grant = self.env["auditlog.attachment.exception"]
                if count < rule.minimum_count and capture and rule.allow_exception:
                    grant = grant._consume(rule, record, actor)
                if count < rule.minimum_count and not grant:
                    raise UserError(self.env._(
                        "%(document)s: %(rule)s requires %(required)s supporting file(s); %(actual)s found.",
                        document=record.display_name, rule=rule.name,
                        required=rule.minimum_count, actual=count,
                    ))

                if capture:
                    self.env["auditlog.attachment.compliance"].sudo().create({
                        "company_id": record.company_id.id,
                        "model_name": record._name,
                        "resource_id": record.id,
                        "resource_name": record.display_name,
                        "rule_name": rule.name,
                        "rule_id": rule.id,
                        "rule_domain": rule.domain_text,
                        "rule_version": rule.revision,
                        "allowed_mimetypes": rule.allowed_mimetypes,
                        "stage": stage,
                        "user_id": actor.id,
                        "operation_key": current_operation() or False,
                        "status": "exception" if grant else "compliant",
                        "exception_id": grant.id if grant else False,
                        "exception_reason": grant.reason if grant else False,
                        "exception_approver_id": grant.approver_id.id if grant else False,
                        "required_count": rule.minimum_count,
                        "actual_count": count,
                        "protect_evidence": rule.protect_evidence,
                        "evidence_ids": [Command.set(evidence.ids)],
                        "evidence_digest": "\n".join(sorted(set(evidence.mapped("checksum")))),
                    })
                    if rule.protect_evidence:
                        evidence._ff_protect_evidence()


class AuditAttachmentCompliance(models.Model):
    _name = "auditlog.attachment.compliance"
    _description = "Supporting Document Compliance"
    _order = "create_date desc, id desc"

    company_id = fields.Many2one("res.company", required=True, index=True)
    model_name = fields.Char(required=True)
    resource_id = fields.Integer(required=True)
    resource_name = fields.Char()
    rule_id = fields.Many2one("auditlog.attachment.rule", ondelete="set null")
    rule_name = fields.Char(required=True)
    rule_domain = fields.Char()
    rule_version = fields.Char()
    allowed_mimetypes = fields.Char()
    stage = fields.Char(required=True)
    user_id = fields.Many2one("res.users")
    operation_key = fields.Char(index=True, readonly=True)
    status = fields.Selection([("compliant", "Compliant"), ("exception", "Authorized exception")], default="compliant", required=True)
    exception_id = fields.Many2one("auditlog.attachment.exception", ondelete="restrict")
    exception_reason = fields.Text()
    exception_approver_id = fields.Many2one("res.users")
    required_count = fields.Integer()
    actual_count = fields.Integer()
    protect_evidence = fields.Boolean()
    evidence_ids = fields.Many2many("ir.attachment")
    evidence_digest = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise UserError(self.env._("Compliance records are created by the control engine."))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(self.env._("Compliance records cannot be changed."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_uninstall(self):
        raise UserError(self.env._("Compliance records cannot be deleted."))


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    ff_audit_evidence = fields.Boolean(
        string="Supporting audit evidence", default=False, copy=False,
        help="Explicitly designated supporting document. Generated PDFs are not counted automatically.",
    )

    @api.constrains("ff_audit_evidence", "type", "file_size", "res_model", "res_id")
    def _check_audit_evidence(self):
        for att in self.filtered("ff_audit_evidence"):
            if att.type != "binary" or att.file_size <= 0 or not att.res_model or not att.res_id or att.res_field:
                raise ValidationError(self.env._("Supporting evidence must be a non-empty file linked to a document."))

    ff_audit_protected = fields.Boolean(default=False, copy=False, readonly=True, index=True)

    def _ff_lock_evidence(self):
        if self:
            self.flush_recordset()
            self.env.cr.execute(SQL(
                "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                SQL.identifier(self._table), tuple(self.ids),
            ))

    def _ff_protect_evidence(self):
        super(IrAttachment, self.sudo()).write({"ff_audit_protected": True})

    @api.model_create_multi
    def create(self, vals_list):
        if any("ff_audit_protected" in vals for vals in vals_list):
            raise UserError(self.env._("Audit protection is managed by the control engine."))
        records = super().create(vals_list)
        if any(records.sudo().mapped("ff_audit_protected")):
            raise UserError(self.env._("Audit protection is managed by the control engine."))
        return records

    def _ff_check_protected(self):
        self._ff_lock_evidence()
        self.invalidate_recordset(["ff_audit_protected"])
        if any(self.sudo().mapped("ff_audit_protected")):
            raise UserError(self.env._("Supporting evidence used in an approved transaction cannot be modified or removed."))

    def write(self, vals):
        if "ff_audit_protected" in vals:
            raise UserError(self.env._("Audit protection is managed by the control engine."))
        sensitive = {"raw", "datas", "db_datas", "store_fname", "checksum", "file_size",
                     "res_model", "res_id", "res_field", "type", "url", "mimetype",
                     "name", "company_id", "ff_audit_evidence", "public", "access_token"}
        if sensitive.intersection(vals):
            self.check_access("write")
            self._ff_check_protected()
        return super().write(vals)

    def unlink(self):
        self.check_access("unlink")
        self._ff_check_protected()
        return super().unlink()


class AuditAttachmentException(models.Model):
    _name = "auditlog.attachment.exception"
    _description = "One-time Attachment Exception"
    _order = "create_date desc"

    rule_id = fields.Many2one("auditlog.attachment.rule", required=True, ondelete="restrict")
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    resource_id = fields.Integer(required=True)
    resource_name = fields.Char(readonly=True)
    actor_id = fields.Many2one("res.users", required=True)
    approver_id = fields.Many2one("res.users", readonly=True)
    reason = fields.Text(required=True)
    expires_at = fields.Datetime(required=True, default=lambda self: fields.Datetime.now() + timedelta(hours=24))
    rule_revision = fields.Datetime(readonly=True)
    rule_version = fields.Char(readonly=True)
    consumed_at = fields.Datetime(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group("flousflow_auditlog.group_attachment_exception"):
            raise UserError(self.env._("Only an exception approver may grant an exception."))
        for vals in vals_list:
            rule = self.env["auditlog.attachment.rule"].browse(vals.get("rule_id")).exists()
            rule.ensure_one()
            rule.check_access("read")
            if not rule.active or not rule.allow_exception:
                raise UserError(self.env._("Exceptions are not enabled for this rule."))
            if rule.company_id not in self.env.companies:
                raise UserError(self.env._("Company is not accessible."))
            record = self.env[rule.model_id.model].browse(vals.get("resource_id")).exists()
            record.ensure_one()
            record.check_access("read")
            if record.company_id != rule.company_id:
                raise UserError(self.env._("Document company must match the rule."))
            actor = self.env["res.users"].browse(vals.get("actor_id")).exists()
            actor.ensure_one()
            if actor == self.env.user or rule.company_id not in actor.company_ids:
                raise UserError(self.env._("Select another authorized company user."))
            if not (vals.get("reason") or "").strip():
                raise UserError(self.env._("A justification is required."))
            expiry = fields.Datetime.to_datetime(vals.get("expires_at") or self.default_get(["expires_at"])["expires_at"])
            if expiry <= fields.Datetime.now() or expiry > fields.Datetime.now() + timedelta(days=7):
                raise UserError(self.env._("Expiry must be within the next seven days."))
            vals.update(company_id=rule.company_id.id, resource_name=record.display_name,
                        approver_id=self.env.uid, rule_revision=rule.write_date,
                        rule_version=rule.revision,
                        consumed_at=False, expires_at=expiry)
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(self.env._("Exception grants cannot be edited."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_uninstall(self):
        raise UserError(self.env._("Exception grants cannot be deleted."))

    @api.model
    def _consume(self, rule, record, actor):
        if not rule.allow_exception or not rule.revision:
            return self.browse()
        grants = self.sudo().search([
            ("rule_id", "=", rule.id), ("company_id", "=", record.company_id.id),
            ("resource_id", "=", record.id), ("actor_id", "=", actor.id),
            ("rule_version", "=", rule.revision), ("consumed_at", "=", False),
            ("expires_at", ">", fields.Datetime.now()),
        ], order="id")
        for grant in grants:
            grant.flush_recordset()
            self.env.cr.execute(SQL("SELECT id FROM %s WHERE id = %s FOR UPDATE",
                                    SQL.identifier(grant._table), grant.id))
            grant.invalidate_recordset(["consumed_at", "expires_at"])
            if grant.consumed_at or grant.expires_at <= fields.Datetime.now():
                continue
            super(AuditAttachmentException, grant).write({"consumed_at": fields.Datetime.now()})
            return grant
        return self.browse()


class AuditEvidenceUpload(models.TransientModel):
    _name = "auditlog.evidence.upload"
    _description = "Upload supporting document"

    model_name = fields.Char(required=True, readonly=True)
    resource_id = fields.Integer(required=True, readonly=True)
    filename = fields.Char()
    data = fields.Binary(attachment=False)

    def _target(self):
        self.ensure_one()
        engine = self.env["auditlog.attachment.rule"]
        if not any(point[0] == self.model_name for point in engine._supported_points()):
            raise UserError(self.env._("Unsupported document."))
        record = self.env[self.model_name].browse(self.resource_id).exists()
        record.ensure_one()
        record.check_access("write")
        if self.model_name == "stock.move" and not record.is_scrap:
            raise UserError(self.env._("Only scrap moves are supported on this model."))
        if record.company_id and record.company_id not in self.env.companies:
            raise UserError(self.env._("Document company is not accessible."))
        return record

    def action_upload(self):
        record = self._target()
        if not self.data or not self.filename:
            raise UserError(self.env._("Select a file to upload."))
        self.env["ir.attachment"].create({
            "name": self.filename, "raw": self.data,
            "res_model": record._name, "res_id": record.id,
            "company_id": record.company_id.id or False,
            "ff_audit_evidence": True,
        })
        return {"type": "ir.actions.act_window_close"}

    def action_existing(self):
        record = self._target()
        view = self.env.ref("flousflow_auditlog.view_supporting_evidence_list")
        return {
            "type": "ir.actions.act_window", "name": self.env._("Supporting documents"),
            "res_model": "ir.attachment", "views": [(view.id, "list")],
            "domain": [
                ("res_model", "=", record._name), ("res_id", "=", record.id),
                ("res_field", "=", False), ("type", "=", "binary"),
                ("file_size", ">", 0),
            ],
            "target": "current",
        }


class AuditControlContext(models.TransientModel):
    _name = "auditlog.control.context"
    _description = "Contextual internal controls"

    model_name = fields.Char(required=True, readonly=True)
    resource_id = fields.Integer(readonly=True)
    move_type = fields.Char(readonly=True)
    picking_type_id = fields.Integer(readonly=True)
    payment_type = fields.Char(readonly=True)
    document_name = fields.Char(readonly=True)
    attachment_status = fields.Selection([
        ("unsupported", "Unsupported operation"),
        ("active", "Active rules"),
        ("inactive", "Inactive rules"),
        ("none", "No rules"),
    ], readonly=True)
    audit_status = fields.Selection([
        ("active", "Active rules"), ("inactive", "Inactive rules"), ("none", "No rules"),
    ], readonly=True)
    can_configure_audit = fields.Boolean(readonly=True)
    can_configure_attachments = fields.Boolean(readonly=True)

    @api.model
    def open_context(self, model_name, record_id=False, move_type=False, picking_type_id=False, payment_type=False):
        can_read_control = (
            self.env.user.has_group("flousflow_auditlog.group_document_control_reader")
            or self.env.user.has_group("flousflow_auditlog.group_auditlog_user")
            or self.env.user.has_group("base.group_system")
        )
        if not can_read_control:
            raise UserError(self.env._("You do not have access to internal control details."))
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model or model_name not in self.env or self.env[model_name]._transient:
            raise UserError(self.env._("Open a supported business document first."))
        self.env[model_name].check_access("read")
        record = self.env[model_name].browse(int(record_id)).exists() if record_id else self.env[model_name].browse()
        record.check_access("read")
        engine = self.env["auditlog.attachment.rule"]
        supported = any(point[0] == model_name for point in engine._supported_points())
        if model_name == "stock.move" and record and not record.is_scrap:
            supported = False
        rules = engine.with_context(active_test=False).search([
            ("model_id", "=", model.id), ("company_id", "=", self.env.company.id),
        ]) if supported else engine.browse()
        if record:
            rules = rules.filtered(lambda rule: bool(record.filtered_domain(literal_eval(rule.domain_text))))
        can_audit = self.env.user.has_group("flousflow_auditlog.group_auditlog_manager")
        can_configure_attachments = (
            self.env.user.has_group("flousflow_auditlog.group_document_control_manager")
            or self.env.user.has_group("base.group_system")
        )
        audit = self.env["auditlog.rule"].search([("model_id", "=", model.id)], limit=1) if can_audit else False
        wizard = self.create({
            "model_name": model_name, "resource_id": record.id or 0,
            "move_type": move_type or False, "picking_type_id": picking_type_id or 0,
            "payment_type": payment_type or False,
            "document_name": record.display_name if record else model.name,
            "attachment_status": "unsupported" if not supported else (
                "active" if any(rules.mapped("active")) else "inactive" if rules else "none"
            ),
            "audit_status": "active" if audit and audit.state == "confirmed" else "inactive" if audit else "none",
            "can_configure_audit": can_audit,
            "can_configure_attachments": can_configure_attachments,
        })
        return {
            "type": "ir.actions.act_window", "name": self.env._("Internal Control"),
            "res_model": self._name, "res_id": wizard.id, "view_mode": "form",
            "views": [(self.env.ref("flousflow_auditlog.view_control_context_form").id, "form")],
            "target": "new",
        }

    def action_attachment_rules(self):
        self.ensure_one()
        if not self.can_configure_attachments:
            raise UserError(self.env._("Only attachment control managers can configure rules."))
        return self.env["auditlog.attachment.rule"].open_contextual_rules(
            self.model_name, self.resource_id, self.move_type, self.picking_type_id, self.payment_type
        )

    def action_audit_rules(self):
        self.ensure_one()
        if not (
            self.env.user.has_group("flousflow_auditlog.group_auditlog_manager")
            or self.env.user.has_group("base.group_system")
        ):
            raise UserError(self.env._("Only global audit managers may configure tracking."))
        model = self.env["ir.model"].sudo().search([("model", "=", self.model_name)], limit=1)
        model.ensure_one()
        self.env[self.model_name].check_access("read")
        action = self.env["ir.actions.actions"]._for_xml_id("flousflow_auditlog.action_auditlog_rule_tree")
        action.update({"domain": [("model_id", "=", model.id)],
                       "context": {"default_model_id": model.id, "default_name": model.name}})
        return action
