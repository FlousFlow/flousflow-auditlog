/** @odoo-module **/
import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

class AttachmentControlSystray extends Component {
    static template = "flousflow_auditlog.AttachmentControlSystray";
    props = useProps({});
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.allowed = signal(false);
        this.busy = signal(false);
        onWillStart(async () => {
            this.allowed.set(await user.hasGroup("flousflow_auditlog.group_document_control_manager"));
        });
    }

    async openRules() {
        if (!this.allowed() || this.busy()) {
            return;
        }
        const controller = this.action.currentController;
        const current = controller?.action;
        if (!current || current.type !== "ir.actions.act_window" || !current.res_model) {
            this.notification.add(_t("Open a supported business document first."), { type: "warning" });
            return;
        }
        this.busy.set(true);
        try {
            const recordId = controller.currentState?.resId || controller.props?.resId || false;
            const moveType = current.context?.default_move_type || false;
            const action = await this.orm.call("auditlog.control.context", "open_context",
                [current.res_model, recordId, moveType, current.context?.default_picking_type_id || false, current.context?.default_payment_type || false]);
            await this.action.doAction(action);
        } finally {
            this.busy.set(false);
        }
    }
}

registry.category("systray").add("flousflow_auditlog.attachment_control", {
    Component: AttachmentControlSystray,
}, { sequence: 35 });
