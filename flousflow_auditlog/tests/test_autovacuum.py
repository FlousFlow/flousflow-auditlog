# Copyright 2016 ABF OSIELL <https://osiell.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import time

from odoo.tests import tagged

from .common import AuditLogRuleCommon


@tagged("post_install", "-at_install")
class TestAuditlogAutovacuum(AuditLogRuleCommon):
    def setUp(self):
        super().setUp()

    def test_autovacuum(self):
        log_model = self.env["auditlog.log"]
        autovacuum_model = self.env["auditlog.autovacuum"]
        partner = self.env["res.partner"].create({"name": "autovacuum test"})
        nb_logs = log_model.search_count(
            [("model_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertGreater(nb_logs, 0)
        # Milliseconds are ignored by autovacuum, waiting 1s ensure that
        # the logs generated will be processed by the vacuum
        time.sleep(1)
        autovacuum_model.autovacuum(days=0)
        nb_logs = log_model.search_count(
            [("model_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertEqual(nb_logs, 0)
