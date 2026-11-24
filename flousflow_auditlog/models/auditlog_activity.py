# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo import fields, models, tools


class AuditlogActivity(models.Model):
    _name = "auditlog.activity"
    _description = "Audit Business Activity"
    _auto = False
    _rec_name = "name"
    _order = "started_at desc, id desc"

    name = fields.Char(readonly=True)
    activity_key = fields.Char(readonly=True)
    kind = fields.Selection([
        ("operation", "Business operation"),
        ("request", "HTTP request"),
        ("technical", "Uncorrelated event"),
    ], readonly=True)
    started_at = fields.Datetime(readonly=True)
    ended_at = fields.Datetime(readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)
    event_count = fields.Integer(readonly=True)
    record_count = fields.Integer(readonly=True)
    model_count = fields.Integer(readonly=True)
    methods = fields.Char(readonly=True)
    example_document = fields.Char(readonly=True)

    def init(self):
        # This is a read-only projection of existing audit logs, not another
        # audit store. No historical technical events are deleted or combined.
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW auditlog_activity AS
            WITH events AS (
                SELECT l.*,
                    COALESCE(NULLIF(l.activity_key, ''), 'Log #' || l.id::text) AS group_key
                FROM auditlog_log l
            )
            SELECT
                MIN(id) AS id,
                group_key AS activity_key,
                CASE WHEN bool_or(operation_key IS NOT NULL AND operation_key != '')
                     THEN regexp_replace(group_key, ' \\[[0-9a-f]{32}\\]$', '')
                     WHEN bool_or(http_request_id IS NOT NULL)
                     THEN 'HTTP request — ' || COALESCE((array_agg(name ORDER BY id)
                         FILTER (WHERE name IS NOT NULL))[1], group_key)
                     ELSE COALESCE(MAX(name), group_key) END AS name,
                CASE WHEN bool_or(operation_key IS NOT NULL AND operation_key != '') THEN 'operation'
                     WHEN bool_or(http_request_id IS NOT NULL) THEN 'request'
                     ELSE 'technical' END AS kind,
                MIN(create_date) AS started_at,
                MAX(create_date) AS ended_at,
                CASE WHEN COUNT(DISTINCT user_id) = 1 AND COUNT(user_id) = COUNT(*)
                     THEN MIN(user_id) ELSE NULL END AS user_id,
                COUNT(*)::integer AS event_count,
                COUNT(DISTINCT (model_model, res_id)) FILTER (WHERE res_id > 0)::integer AS record_count,
                COUNT(DISTINCT model_model)::integer AS model_count,
                string_agg(DISTINCT method, ', ' ORDER BY method) AS methods,
                (array_agg(name ORDER BY id) FILTER (WHERE name IS NOT NULL))[1] AS example_document
            FROM events
            GROUP BY group_key
        """)

    def action_open_events(self):
        self.ensure_one()
        self.check_access("read")
        domain = [("activity_key", "=", self.activity_key)]
        if self.kind == "technical" and self.activity_key == "Log #%s" % self.id:
            domain = [("id", "=", self.id)]
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "auditlog.log",
            "view_mode": "list,form",
            "domain": domain,
            "context": {},
        }

    def action_open_compliance(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Document Compliance"),
            "res_model": "auditlog.attachment.compliance",
            "view_mode": "list,form",
            "domain": [("operation_key", "=", self.activity_key)] if self.kind == "operation" else [("id", "=", 0)],
        }
