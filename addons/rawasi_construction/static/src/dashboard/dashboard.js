/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RawasiDashboard extends Component {
    static template = "rawasi_construction.Dashboard";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({ loaded: false, data: { cards: [] } });

        onWillStart(async () => {
            const data = await this.orm.call(
                "rawasi.dashboard.kpi",
                "get_dashboard_data",
                []
            );
            this.state.data = data;
            this.state.loaded = true;
        });
    }

    async openCard(card) {
        const ctx = card.context || {};
        const extraDomain = card.domain || [];

        // لو البطاقة فيها domain إضافي، نفتح أكشن مباشر بالموديل + الـ domain
        if (extraDomain.length) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: card.title,
                res_model: this._modelFromAction(card.action),
                domain: extraDomain,
                context: ctx,
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
            return;
        }

        // وإلا نفتح الأكشن الرسمي بـ xmlid (يحترم search_view_id والـ default filters)
        this.action.doAction(card.action, {
            additionalContext: ctx,
        });
    }

    _modelFromAction(xmlid) {
        // خرائط احتياط لو ما قدر يجيب الموديل من xml id
        const map = {
            "rawasi_construction.action_rawasi_competition": "rawasi.competition",
            "rawasi_construction.action_variation_order": "rawasi.variation.order",
            "rawasi_construction.action_payment_certificate": "rawasi.payment.certificate",
            "rawasi_construction.action_ncr": "rawasi.ncr",
            "rawasi_construction.action_bank_guarantee": "rawasi.bank.guarantee",
            "rawasi_construction.action_import_batch": "rawasi.import.batch",
            "rawasi_construction.action_material_request": "rawasi.material.request",
            "rawasi_construction.action_daily_report": "rawasi.daily.report",
            "rawasi_construction.action_material_approval": "rawasi.material.approval",
            "rawasi_construction.action_rfi": "rawasi.rfi",
        };
        return map[xmlid] || "";
    }

    openUserGuide() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "دليل الاستخدام",
            res_model: "rawasi.user.guide",
            views: [[false, "kanban"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("rawasi_dashboard", RawasiDashboard);
