#!/usr/bin/env bash
set -euo pipefail
# Run on a disposable PostgreSQL database only.
: "${ODOO_SOURCE:?Set ODOO_SOURCE to an Odoo 20 Community checkout}"
: "${AUDIT_TEST_DB:?Set AUDIT_TEST_DB to a fresh disposable database}"
case "$AUDIT_TEST_DB" in ff_audit_test_*) ;; *) echo "Database must start with ff_audit_test_" >&2; exit 2;; esac
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" "$ODOO_SOURCE/odoo-bin" --version
"$PYTHON" "$ODOO_SOURCE/odoo-bin" --addons-path="$ODOO_SOURCE/addons,$ROOT" \
    -d "$AUDIT_TEST_DB" --without-demo=all --stop-after-init --test-enable \
    -i flousflow_auditlog,flousflow_auditlog_sale_control,flousflow_auditlog_purchase_control,flousflow_auditlog_account_control,flousflow_auditlog_stock_control,flousflow_auditlog_mrp_control "$@"
