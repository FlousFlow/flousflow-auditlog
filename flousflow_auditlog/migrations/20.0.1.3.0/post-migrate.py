"""Remove retired HTTP/session and standalone field-change artifacts."""

def migrate(cr, version):
    if not version:
        return

    xmlids = (
        "menu_action_auditlog_http_request_tree",
        "menu_action_auditlog_http_session_tree",
        "menu_auditlog_line",
        "action_auditlog_http_request_tree",
        "action_auditlog_http_session_tree",
        "action_auditlog_line",
        "view_auditlog_http_request_form",
        "view_auditlog_http_request_tree",
        "view_auditlog_http_request_search",
        "view_auditlog_http_session_form",
        "view_auditlog_http_session_tree",
        "view_auditlog_http_session_search",
        "view_auditlog_line_tree",
        "view_auditlog_line_search",
        "access_auditlog_http_session_user",
        "access_auditlog_http_request_user",
        "access_auditlog_http_session_manager",
        "access_auditlog_http_session_system_create",
        "access_auditlog_http_request_manager",
        "access_auditlog_http_request_system_create",
        "access_auditlog_log_line_view_manager",
    )
    for model, table in (
        ("ir.ui.menu", "ir_ui_menu"),
        ("ir.actions.act_window", "ir_actions"),
        ("ir.ui.view", "ir_ui_view"),
        ("ir.model.access", "ir_access"),
    ):
        cr.execute(
            f"""
            DELETE FROM {table} target
            USING ir_model_data data
            WHERE data.module = 'flousflow_auditlog'
              AND data.name = ANY(%s)
              AND data.model = %s
              AND data.res_id = target.id
            """,
            (list(xmlids), model),
        )
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'flousflow_auditlog' AND name = ANY(%s)",
        (list(xmlids),),
    )
    cr.execute("DROP VIEW IF EXISTS auditlog_activity CASCADE")
    cr.execute("ALTER TABLE auditlog_log DROP COLUMN IF EXISTS http_session_id")
    cr.execute("ALTER TABLE auditlog_log DROP COLUMN IF EXISTS http_request_id")
    cr.execute("DROP TABLE IF EXISTS auditlog_http_request CASCADE")
    cr.execute("DROP TABLE IF EXISTS auditlog_http_session CASCADE")
