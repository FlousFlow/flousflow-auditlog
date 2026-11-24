# Copyright 2015 ABF OSIELL <https://osiell.com>
# Flous Flow integration metadata and packaging changes: Copyright 2026 Flous Flow
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Flous Flow Audit Log",
    "version": "20.0.1.1.0",
    "author": "Flous Flow (integration), ABF OSIELL, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://flousflow.com",
    "support": "support@flousflow.com",
    "summary": "Track who created, read, changed, or deleted Odoo records",
    "images": ["static/description/logs.png"],
    "category": "Tools",
    "depends": ["base", "web"],
    "data": [
        "security/res_groups.xml",
        "security/ir.access.csv",
        "data/ir_cron.xml",
        "views/menu.xml",
        "views/auditlog_http_request_views.xml",
        "views/auditlog_http_session_views.xml",
        "views/auditlog_log_line_views.xml",
        "views/auditlog_log_views.xml",
        "views/auditlog_rule_views.xml",
        "views/attachment_control_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "flousflow_auditlog/static/src/js/control_systray.js",
            "flousflow_auditlog/static/src/xml/control_systray.xml",
        ],
    },
    "application": True,
    "installable": True,
}
