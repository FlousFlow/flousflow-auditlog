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
