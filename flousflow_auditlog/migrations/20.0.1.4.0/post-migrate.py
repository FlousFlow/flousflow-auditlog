"""Remove the obsolete manual Audit Rules menu."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        DELETE FROM ir_ui_menu menu
        USING ir_model_data data
        WHERE data.module = 'flousflow_auditlog'
          AND data.name = 'menu_action_auditlog_rule_tree'
          AND data.model = 'ir.ui.menu'
          AND data.res_id = menu.id
        """
    )
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'flousflow_auditlog' AND name = 'menu_action_auditlog_rule_tree'"
    )
