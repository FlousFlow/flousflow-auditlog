# Odoo 20 Engineering Log

## 2026-11-25 — Contextual internal-control entry point

- **Problem:** The internal-control flow was hidden unless the current user had the document-control-manager group, and there was no dependable entry point from a normal Odoo screen.
- **Evidence:** The systray component was restricted to `group_document_control_manager`; the purchase list did not expose the control entry point. Server-side rule configuration remains permission-protected.
- **Decision:** Keep one standard Odoo systray entry point available in backend screens, open a context wizard for the current model/record, and enforce reader/configuration permissions in Python and ACLs. Managers can open contextual document rules; readers can inspect status only.
- **Tests:** Static checks passed for 59 files; the sale-control suite passed 8/8 tests; browser smoke test opened the button from the purchase list, the contextual status dialog, and a purchase-order-scoped rule form.
- **Boundary:** The audit feed records configured audit rules and installed business-operation adapters; it does not automatically mean every possible Odoo event is captured without configuration.

## 2026-11-25 — Retire HTTP/session and standalone field-change features

- **Problem:** The module exposed technical HTTP requests, user sessions, and a standalone field-change projection that were not part of the required internal-control workflow.
- **Decision:** Remove those models, views, menus, ACLs, tests, log relations, and new-event capture. Keep the core CRUD audit event and Activity Feed. Add an upgrade migration that removes legacy UI records, tables, and log columns from existing databases.
- **Tests:** Static checks passed for 52 files; the sale-control upgrade/test command completed successfully; database verification showed the retired tables, columns, and external IDs were removed.
- **Risk:** Existing historical HTTP/session metadata is intentionally deleted by the migration. Field-level lines attached to core audit logs remain internal to preserve existing audit record compatibility, but the standalone Field Changes feature is gone.

## 2026-11-25 — Automatic business-operation auditing

- **Problem:** Users were required to create and confirm audit rules before any activity appeared.
- **Decision:** Automatically patch business models for create, write, unlink, and export operations at registry load. Technical framework, messaging, permissions, and auditlog models are excluded to avoid recursion and noise; manual Audit Rules navigation is removed.
- **Tests:** A live Odoo shell smoke test created and updated a `res.partner` without any rule and observed `create` and `write` audit events. Static checks passed for 53 files. The legacy opt-in test suite is not compatible with the new always-on contract and reports failures because it expects models to remain unpatched until a rule is confirmed.

## 2026-11-25 — Remove technical log UI

- **Problem:** The standalone Detailed Logs screen and Technical Details action exposed low-level audit storage instead of a usable business view.
- **Decision:** Remove the detailed-log views, action, menu, and Activity Feed drill-down action. Keep only the Activity Feed projection and internal audit storage required to aggregate business operations.
- **Tests:** Upgrade completed successfully; database verification found no remaining external IDs for the retired technical-log UI; HTTP smoke check returned 200; static checks passed for 54 files.

## 2026-11-25 — Remove compliance status screen, retain enforcement

- **Problem:** The Compliance Status list/form was confusing to users and duplicated the enforcement engine.
- **Decision:** Remove only its menu, action, list/form views, and Activity Feed button. Keep `auditlog.attachment.compliance` records, evidence checks, exceptions, protection, and all operation adapters so missing documents remain enforced.
- **Tests:** Static checks passed for 55 files; module upgrade completed successfully; Odoo server restarted on port 8072.

## 2026-11-25 — Business summary and source-document link

- **Problem:** Activity rows showed repeated raw events and technical-looking names, with no route back to the source record.
- **Decision:** Add an Arabic human-readable summary and a `فتح المستند` action. The activity projection now carries the source model and record IDs, opening the original Odoo form (or list for multiple records).
- **Follow-up:** Automatic CRUD logging now wraps each ORM call in one operation scope, so batch creates/updates/deletes appear as one total row with a record count and a source-document list link.
- **UI follow-up:** Added the same standard Odoo `فتح المستند` header action to the activity detail form, so the source record is reachable from both list and detail views.
- **Aggregation follow-up:** Legacy rows without an operation key are now grouped conservatively by user, method, and exact execution timestamp in the read-only Activity Feed projection; raw audit rows remain untouched.
- **Operation-scope correction:** The scope now wraps the full ORM method, including nested model work, so one user action produces one shared activity key instead of separate rows for internal child records.
- **Clarity follow-up:** Activity list and detail views now show both the exact document name and its user-facing document type (for example, `المنتج`), not only the free-text summary.
- **Change-detail follow-up:** Write activities now expose the changed field labels from the audit lines (for example, `فئة المنتج`) in both the summary and a dedicated `تفاصيل التغيير` field.
- **Before/after follow-up:** Change details now render each field as `من <old> إلى <new>`, using `فارغ` for an empty side.
- **Contextual-rule button:** The systray control is now visibly labeled `قاعدة المستندات` and opens the attachment-rule form directly with the current model/record defaults.
- **Standard systray styling:** The visible label was removed per UX feedback; the control now uses Odoo's standard icon-only systray button pattern and `oi` security icon.

## 2026-11-25 — Accounting attachment-control regression coverage

- **Problem:** Invoice and journal-entry enforcement was installed but had no dedicated automated regression tests.
- **Decision:** Add account-integration tests for contextual rule defaults, supported posting points, and the missing-evidence/accepted-evidence paths for customer invoices and journal entries.
- **Tests:** The new test class uses Odoo's accounting test fixtures and verifies that failed posting remains draft while valid designated evidence allows posting.

## 2026-11-25 — Default activation for contextual accounting rules

- **Problem:** A purchase-invoice rule could be saved inactive, so posting correctly found no applicable enforcement rule and proceeded.
- **Decision:** New attachment rules, especially those opened from a document's contextual button, default to active; users can still explicitly deactivate them. The existing local purchase-invoice rule was activated after verification.
- **Verification:** After upgrading and restarting the local Odoo server, a purchase invoice posted as the accounting user without evidence was blocked with the required-file message; the rule is persisted active in the development database.
