"""Remove the compliance status UI while preserving enforcement records."""


def migrate(cr, version):
    if not version:
        return
    records = (
        ("ir.ui.menu", "ir_ui_menu", "menu_compliance"),
        ("ir.actions.act_window", "ir_actions", "action_compliance"),
        ("ir.ui.view", "ir_ui_view", "view_compliance_list"),
        ("ir.ui.view", "ir_ui_view", "view_compliance_form"),
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
