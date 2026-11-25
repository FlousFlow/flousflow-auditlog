# Copyright 2016 ABF OSIELL <https://osiell.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class AuditlogAutovacuum(models.TransientModel):
    _name = "auditlog.autovacuum"
    _description = "Auditlog - Delete old logs"

    @api.model
    def autovacuum(self, days, chunk_size=None):
        """Delete CRUD audit logs older than ``days``. Called from a cron."""
        if not self.env.su and not self.env.user.has_group("flousflow_auditlog.group_auditlog_manager"):
            raise AccessError(self.env._("Only global audit managers may purge audit logs."))
        days = (days > 0) and int(days) or 0
        deadline = datetime.now() - timedelta(days=days)
        data_models = ("auditlog.log",)
        for data_model in data_models:
            records = self.env[data_model].sudo().search(
                [("create_date", "<=", fields.Datetime.to_string(deadline))],
                limit=chunk_size,
                order="create_date asc",
            )
            nb_records = len(records)
            records.unlink()
            _logger.info("AUTOVACUUM - %s '%s' records deleted", nb_records, data_model)
        return True
