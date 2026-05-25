/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

// Phase 0 placeholder dashboard. KPI widgets are added in later phases.
export class RawasiDashboard extends Component {
    static template = "rawasi_construction.Dashboard";
}

registry.category("actions").add("rawasi_dashboard", RawasiDashboard);
