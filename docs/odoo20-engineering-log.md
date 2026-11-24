# Odoo 20 Engineering Log

## 2026-11-25 — Contextual internal-control entry point

- **Problem:** The internal-control flow was hidden unless the current user had the document-control-manager group, and there was no dependable entry point from a normal Odoo screen.
- **Evidence:** The systray component was restricted to `group_document_control_manager`; the purchase list did not expose the control entry point. Server-side rule configuration remains permission-protected.
- **Decision:** Keep one standard Odoo systray entry point available in backend screens, open a context wizard for the current model/record, and enforce reader/configuration permissions in Python and ACLs. Managers can open contextual document rules; readers can inspect status only.
- **Tests:** Static checks passed for 59 files; the sale-control suite passed 8/8 tests; browser smoke test opened the button from the purchase list, the contextual status dialog, and a purchase-order-scoped rule form.
- **Boundary:** The audit feed records configured audit rules and installed business-operation adapters; it does not automatically mean every possible Odoo event is captured without configuration.
