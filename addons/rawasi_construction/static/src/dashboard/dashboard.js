/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RawasiDashboard extends Component {
    static template = "rawasi_construction.Dashboard";

    setup() {
        this.action = useService("action");
        this.state = useState({});
    }

    openUserGuide() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "دليل الاستخدام",
            res_model: "rawasi.user.guide",
            views: [[false, "kanban"], [false, "form"]],
            target: "current",
            context: { search_default_g_type: 1 },
        });
    }
}

registry.category("actions").add("rawasi_dashboard", RawasiDashboard);
