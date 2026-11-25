# Copyright 2026 Flous Flow
# License AGPL-3.0 or later.
from odoo import api, fields, models, tools


class AuditlogActivity(models.Model):
    _name = "auditlog.activity"
    _description = "Audit Business Activity"
    _auto = False
    _rec_name = "name"
    _order = "started_at desc, id desc"

    name = fields.Char(readonly=True)
    activity_key = fields.Char(readonly=True)
    kind = fields.Selection([("operation", "Business operation")], readonly=True)
    started_at = fields.Datetime(readonly=True)
    ended_at = fields.Datetime(readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)
    event_count = fields.Integer(readonly=True)
    record_count = fields.Integer(readonly=True)
    model_count = fields.Integer(readonly=True)
    methods = fields.Char(readonly=True)
    operation_summary = fields.Char(compute="_compute_operation_summary", readonly=True)
    change_details = fields.Char(readonly=True)
    example_document = fields.Char(readonly=True)
    model_name = fields.Char(readonly=True)
    model_model = fields.Char(readonly=True)
    resource_ids = fields.Char(readonly=True)
    display_summary = fields.Char(compute="_compute_display_summary", readonly=True)

    @api.depends("methods")
    def _compute_operation_summary(self):
        labels = {"create": "إنشاء", "write": "تعديل", "unlink": "حذف", "export_data": "تصدير"}
        for activity in self:
            activity.operation_summary = ", ".join(
                labels.get(method.strip(), method.strip())
                for method in (activity.methods or "").split(",")
                if method.strip()
            )

    @api.depends("user_id", "operation_summary", "example_document", "change_details")
    def _compute_display_summary(self):
        for activity in self:
            user = activity.user_id.display_name if activity.user_id else "المستخدم"
            action = activity.operation_summary or "نفذ حركة"
            document = activity.example_document or "مستند"
            details = f" — التفاصيل: {activity.change_details}" if activity.change_details else ""
            activity.display_summary = f"{user} قام بـ {action} على {document}{details}"

    def init(self):
        # This is a read-only projection of existing audit logs, not another
        # audit store. Historical rows without an operation key are grouped
        # conservatively by user, method, and exact execution timestamp.
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW auditlog_activity AS
            WITH line_summaries AS (
                SELECT log_id,
                    string_agg(DISTINCT format(
                        '%s: من %s إلى %s',
                        field_description,
                        COALESCE(NULLIF(btrim(old_value_text), ''), 'فارغ'),
                        COALESCE(NULLIF(btrim(new_value_text), ''), 'فارغ')
                    ), ', ') AS change_details
                FROM auditlog_log_line
                WHERE field_description IS NOT NULL AND field_description != ''
                GROUP BY log_id
            ), events AS (
                SELECT l.*,
                    CASE WHEN l.method = 'write' THEN ls.change_details END AS change_details,
                    CASE
                        WHEN l.operation_key IS NOT NULL AND l.operation_key != ''
                            THEN l.operation_key
                        ELSE format(
                            'legacy|%s|%s|%s',
                            COALESCE(l.user_id, 0),
                            COALESCE(l.method, ''),
                            l.create_date
                        )
                    END AS group_key
                FROM auditlog_log l
                LEFT JOIN line_summaries ls ON ls.log_id = l.id
            )
            SELECT
                MIN(id) AS id,
                group_key AS activity_key,
                CASE WHEN bool_or(operation_key IS NOT NULL AND operation_key != '')
                     THEN regexp_replace(group_key, ' \\[[0-9a-f]{32}\\]$', '')
                     ELSE COALESCE(MAX(name), group_key) END AS name,
                'operation' AS kind,
                MIN(create_date) AS started_at,
                MAX(create_date) AS ended_at,
                CASE WHEN COUNT(DISTINCT user_id) = 1 AND COUNT(user_id) = COUNT(*)
                     THEN MIN(user_id) ELSE NULL END AS user_id,
                COUNT(*)::integer AS event_count,
                COUNT(DISTINCT (model_model, res_id)) FILTER (WHERE res_id > 0)::integer AS record_count,
                COUNT(DISTINCT model_model)::integer AS model_count,
                string_agg(DISTINCT method, ', ' ORDER BY method) AS methods,
                string_agg(DISTINCT change_details, ', ') FILTER (WHERE change_details IS NOT NULL) AS change_details,
                (array_agg(name ORDER BY
                    CASE
                        WHEN model_model = 'product.template' THEN 0
                        WHEN model_model IN ('product.product', 'product.value') THEN 1
                        ELSE 0
                    END,
                    id
                ) FILTER (WHERE name IS NOT NULL))[1] AS example_document,
                COALESCE(
                    MIN(model_name) FILTER (WHERE model_model = 'product.template'),
                    MIN(model_name)
                ) AS model_name,
                COALESCE(
                    MIN(model_model) FILTER (WHERE model_model = 'product.template'),
                    MIN(model_model)
                ) AS model_model,
                COALESCE(
                    string_agg(DISTINCT res_id::text, ',') FILTER (
                        WHERE res_id > 0 AND model_model = 'product.template'
                    ),
                    string_agg(DISTINCT res_id::text, ',') FILTER (WHERE res_id > 0)
                ) AS resource_ids
            FROM events
            GROUP BY group_key
        """)

    def action_open_document(self):
        self.ensure_one()
        self.check_access("read")
        if not self.model_model or not self.resource_ids:
            return False
        ids = [int(value) for value in self.resource_ids.split(",") if value.isdigit()]
        records = self.env[self.model_model].browse(ids).exists()
        if not records:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.example_document or self.display_summary,
            "res_model": self.model_model,
            "view_mode": "list,form" if len(records) > 1 else "form",
            "res_id": records.id if len(records) == 1 else False,
            "domain": [("id", "in", records.ids)] if len(records) > 1 else [],
            "target": "current",
        }
