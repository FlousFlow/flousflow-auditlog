# Odoo 20 development branch — NOT a release

Original base: 19.0 at 724b754df1b9fbd878c56b64a4192872e2d1298b.
Odoo upstream source inspected: d2a79d46ca412077759b0d4fb5caa0ffbfec3bd5.

## Implemented development increments
- Grouped Business Activity plus unchanged raw Technical Logs. Explicit server-side operation scope takes precedence; HTTP request + user fallback is not a guarantee of a business operation. Old/no-request logs stay separate.
- Rule model, per-company scope, minimum evidence count and safe literal domain conditions, user/group filters. Inactive by default. Unsupported active rules rejected.
- Contextual Systray button (manager only), opens rules for current supported model and company. Defaults the accounting domain to the detected move type where available. Not a modal or live status indicator yet.
- Optional auto-install technical bridges for Sales, Purchase and Accounting. All configuration lives in the original app; the bridges avoid installing unrelated Odoo apps. Verified the relevant Odoo 20 source method names. Checks on transition to sale/purchase/posted; checks after create and write; standard transaction rollback expected. Scope wraps standard action calls.
- Evidence designation via standard attachment list (Action > Supporting documents) after upload in Chatter. Only explicitly marked, non-empty binary files with distinct checksums are counted. This is manual designation, not automatic provenance detection.
- Tests added for operation scope and the sale evidence checker; not executed.
- Preserve AGPL-3 and original author notices; branch 19.0 unchanged.

## Release blockers
- Odoo 20 runtime installation, upgrade, UI, integration and security tests NOT run. Verify all inherited legacy hooks, XMLIDs and assets.
- Verify bridge behavior with custom workflows, rollback, sudo/automation, direct state manipulation, and batch operations. No claim of complete bypass prevention.
- No inventory/manufacturing/payment adapters yet. No cross-request business correlation, business summary rows, complete translations, deletion/reassignment protection, secure provenance classification, compliance snapshots, exception flow, reporting or audit retention upgrade yet.
- Existing OCA-based technical logs and permissions are preserved; additional hardening needed.
- Do not publish or deploy this WIP branch as a production release.

## Third development increment
- Stock picking completion, manufacturing confirmation/completion and unbuild completion adapters use inspected Odoo 20 lifecycle methods; backorder/wizard paths and direct stock moves still require runtime coverage.
- Add read-only per-rule compliance snapshots (including file hashes), company-scoped report, default-on strict protection of all designated evidence used in successful checks. Protection persists if the rule is disabled; no replacement/unlock workflow yet.
- Serialize evidence verification and mutation with attachment-row locks; concurrency and rollback tests are still required. No guarantee against direct SQL or administrator-level code.
- Contextual defaults now support exact picking operation type when known. Generic listing may still need manual domain selection.
- Original release blockers above remain except where implemented here. Payment, scrap, adjustment, exception and secure upload provenance remain pending. No production readiness claim.

Added regression tests for protected evidence, snapshot immutability, and duplicate hashes. Runtime tests remain unexecuted.

## Fourth development increment
- Payment posting, company-scoped quant adjustment, and scrap stock.move completion hooks; Odoo 20 upstream no longer contains stock.scrap model in stock. Quant evidence previously captured for the same quant is excluded. Shared-company quant locations do not match company-specific rules. Adjustment checks are pre-application and need rollback/zero-move tests. Scrap hook coverage of alternative creation and move splitting remains unverified.
- One-use exception grant requires separate approver, target rule and document, another user, mandatory reason and expiry within seven days. Rule change invalidates grant. Consumption uses a row lock and is recorded in the compliance snapshot. Defaults off. Grant creation UI currently uses resource ID; no contextual request wizard or cancellation yet.
- Prevent context defaults from setting protected attachment flag on create.
- No runtime tests yet; all new integration points and access controls need installation, functional and security tests. Payment registration wizard and automatically generated moves require particular attention.

## Evidence UX and regression follow-up
- Standard transient upload wizard directly creates designated ir.attachment evidence after checking target document write permission; also offers existing attachment designation. Usable on a saved record even without chatter. No new binary storage.
- Correct quant hash filtering to compare previous compliance for the same rule, avoiding a new rule's current capture blocking a second applicable rule. Reuse across distinct rules is intentional. Quant lifetime/recreation and historical hash persistence still need review.
- Store operation key on compliance snapshots when a trusted scope exists.
- Expose Audit parent menu to the audit group, rather than system administrators only. Existing raw audit access requires separate hardening review.
- Added wizard and one-use exception regression test source; not executed. No CI/runtime setup verified.

## Fifth increment: one row per correlated activity
- Read-only SQL projection auditlog.activity, with one row per trusted operation key, HTTP request/user fallback or individual uncorrelated event. Original logs remain the authority. Standard list, form and search views, exact drill-down, event/record counts and compliance link. Operation labels include document name when a single root record is available. Batch actions remain one operation with multiple records; no time-based merging. HTTP request fallback is labelled as such, not a verified business transaction.
- Summary access intentionally matches the existing global audit reader role; legacy audit records do not provide reliable company ownership. Company-isolated technical audit access remains a blocker; do not grant this role to branch-restricted users.
- Summary is a live projection; row IDs can change if underlying logs are purged. Retention and large-volume SQL performance still need tests.
- Added Odoo regression test source and disposable database test runner scripts/test-odoo20.sh. Runtime not executed in this environment: Docker/PostgreSQL binaries unavailable and direct GitHub checkout cannot resolve host.

## Automated quality gate configuration
- Added static manifest, Python syntax, XML and ACL checks, and a GitHub Actions workflow for fresh installation and same-version upgrade against pinned Odoo 20 and PostgreSQL 16. This is not a tested migration from 19 databases. Workflow results must be inspected before release. Integration tests do not yet cover every required security, concurrency, UX or performance case.

## Security boundary follow-up
- Global technical audit is deliberately restricted to explicitly named all-company audit roles. A separate company-scoped document reader/manager and exception approver can access document rules and compliance without global raw logs. Existing global audit role membership retains its all-company scope. Review current users before deploying, particularly accounts previously assigned global reader through exception role.
- Technical log ACLs are read-only for managers; retention is still a separately authorized purge method. Global audit administrators/server operators are not a tamper-proof adversary boundary.
- Company consistency and MIME filters for supporting evidence; rule revision UUID invalidates previously issued exception grants after a rule edit (including same-second edits).
- No claim of record-level partitioning of raw technical logs: arbitrary model fields may contain another company's data, so use scoped roles for branch users. Runtime verification pending.

## Contextual control UI
- Standard modal opens from shield, showing attachment rule status and (only for global audit managers) audit tracking status; opens relevant rule list with model/company defaults. On saved records, rule status matches actual business domain. On list views, status is model-level rather than a guarantee of each document's coverage.
- Standard Odoo 20 domain widget replaces the raw technical text field, with expressions disabled. Actual domain validation remains server-side.
- Correct exception approver implied group to company document reader (not global audit reader).
- UI and backend security tests still required.

## Real CI result and fix
- First static gate passed; fresh install failed at registry field setup: Odoo 20 forbids restrict ondelete to ir.model. Changed rule model link to cascade (a model that is removed cannot retain a live control rule; test uninstall separately).
- Scope test tags to this module suite, improve CI failure diagnostics and use explicit PostgreSQL health-check database.
- Arabic catalog updates for new menus, views, fields, stages and access groups; existing catalog is incomplete and runtime translation import still needs verification.
