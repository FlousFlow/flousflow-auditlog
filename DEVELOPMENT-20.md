# Odoo 20 development branch — not a release

Base: 19.0 at 724b754df1b9fbd878c56b64a4192872e2d1298b. Upstream Odoo 20 inspected at d2a79d46ca412077759b0d4fb5caa0ffbfec3bd5.

Implemented first increment:
- Preserve raw auditlog.log and auditlog.log.line.
- Group list by trusted scoped operation key, else HTTP request and user, else separate technical log. HTTP group is a request, not a guaranteed business operation. Old logs without request stay separate.
- Add server-side operation scope helper. Adapters must explicitly open a scope.
- Add attachment rule model, access controls, company domain, rule configuration and server checker for explicitly designated supporting evidence. Rules cannot be activated without an installed adapter.
- Correct legacy auditlog security XMLID references in reviewed files.
- Preserve AGPL-3 and original author notices.

Release blockers: Odoo 20 installation, upgrade and tests not run; verify all existing monkey patches and XML IDs; no lifecycle adapter or contextual Systray in this increment; evidence selection UI, provenance hardening, immutable compliance, deletion protection and exceptions not yet implemented. Do not publish or deploy as a finished release. No change to branch 19.0.
