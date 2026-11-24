/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

class AttachmentControlSystray extends Component {
    static template = "flousflow_auditlog.AttachmentControlSystray";
    static props = {};
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ allowed: false, busy: false });
        onWillStart(async () => {
            this.state.allowed = await user.hasGroup("flousflow_auditlog.group_auditlog_manager");
        });
    }

    async openRules() {
        if (!this.state.allowed || this.state.busy) {
            return;
        }
        const controller = this.action.currentController;
        const current = controller?.action;
        if (!current || current.type !== "ir.actions.act_window" || !current.res_model) {
            this.notification.add(_t("Open a supported business document first."), { type: "warning" });
            return;
        }
        this.state.busy = true;
        try {
            const recordId = controller.currentState?.resId || controller.props?.resId || false;
            const moveType = current.context?.default_move_type || false;
            const action = await this.orm.call("auditlog.attachment.rule", "open_contextual_rules",
                [current.res_model, recordId, moveType]);
            await this.action.doAction(action);
        } finally {
            this.state.busy = false;
        }
    }
}

registry.category("systray").add("flousflow_auditlog.attachment_control", {
    Component: AttachmentControlSystray,
}, { sequence: 35 });
