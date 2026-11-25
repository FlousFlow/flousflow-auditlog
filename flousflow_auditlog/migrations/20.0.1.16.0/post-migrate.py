"""Backfill readable labels for historical many2one audit changes."""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env["auditlog.log.line"].search([])
    for line in lines:
        field = line.field_id
        if field.ttype != "many2one" or not field.relation or field.relation not in env.registry.models:
            continue
        relation = env[field.relation].sudo()

        def label(value):
            try:
                value = int(value or 0)
            except (TypeError, ValueError):
                value = 0
            return relation.browse(value).display_name if value else ""

        cr.execute(
            """
            UPDATE auditlog_log_line
               SET old_value_text = %s,
                   new_value_text = %s
             WHERE id = %s
            """,
            (label(line.old_value), label(line.new_value), line.id),
        )
