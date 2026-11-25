"""Remove the retired technical log user interface."""


def migrate(cr, version):
    if not version:
        return
    records = (
        ("ir.ui.menu", "ir_ui_menu", "menu_audit_logs"),
        ("ir.actions.act_window", "ir_actions", "action_auditlog_log_tree"),
        ("ir.ui.view", "ir_ui_view", "view_auditlog_log_form"),
        ("ir.ui.view", "ir_ui_view", "view_auditlog_log_tree"),
        ("ir.ui.view", "ir_ui_view", "view_auditlog_log_search"),
    )
    for model, table, xmlid in records:
        cr.execute(
            f"""
            DELETE FROM {table} target
            USING ir_model_data data
            WHERE data.module = 'flousflow_auditlog'
              AND data.name = %s
              AND data.model = %s
              AND data.res_id = target.id
            """,
            (xmlid, model),
        )
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = 'flousflow_auditlog' AND name = %s",
            (xmlid,),
        )
