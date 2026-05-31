# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiUnifiedDashboard(models.TransientModel):
    """لوحة مالك رواسي الموحدة — تجمع مؤشرات المقاولات + الورشة + التصنيع الداخلي."""

    _name = "rawasi.dashboard.unified"
    _description = "لوحة رواسي الموحدة"

    # المقاولات
    active_projects = fields.Integer(string="مشاريع نشطة", readonly=True)
    competitions_open = fields.Integer(string="منافسات نشطة", readonly=True)
    ipc_pending = fields.Integer(string="مستخلصات بانتظار الاعتماد", readonly=True)
    guarantees_expiring = fields.Integer(string="ضمانات تنتهي خلال 90 يوم", readonly=True)

    # الورشة
    mo_in_production = fields.Integer(string="أوامر تصنيع قيد العمل", readonly=True)
    mo_awaiting_payment = fields.Integer(string="بانتظار سداد", readonly=True)
    mo_ready_delivery = fields.Integer(string="جاهز للتسليم", readonly=True)

    # التصنيع الداخلي
    internal_active = fields.Integer(string="أوامر تصنيع داخلي نشطة", readonly=True)
    internal_value = fields.Monetary(string="قيمة التصنيع الداخلي", currency_field="currency_id", readonly=True)

    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update(self._compute_kpis())
        return res

    @api.model
    def _compute_kpis(self):
        Project = self.env["project.project"]
        Comp = self.env["rawasi.competition"]
        Ipc = self.env["rawasi.ipc"]
        Bg = self.env["rawasi.bank.guarantee"]
        Mo = self.env["rawasi.workshop.mo"]
        Iwo = self.env["rawasi.internal.workshop.order"]

        internal_active = Iwo.search(
            [("state", "in", ("sale_pending", "confirmed", "in_production"))]
        )
        return {
            "active_projects": Project.search_count([("rawasi_is_construction", "=", True)]),
            "competitions_open": Comp.search_count(
                [("state", "in", ("draft", "pricing", "submitted"))]
            ),
            "ipc_pending": Ipc.search_count([("state", "=", "submitted")]),
            "guarantees_expiring": Bg.search_count(
                [("state", "=", "active"), ("days_to_expiry", "<=", 90)]
            ),
            "mo_in_production": Mo.search_count([("state", "=", "in_production")]),
            "mo_awaiting_payment": Mo.search_count(
                [("state", "=", "confirmed"), ("is_internal", "=", False)]
            ),
            "mo_ready_delivery": Mo.search_count([("state", "=", "done")]),
            "internal_active": len(internal_active),
            "internal_value": sum(internal_active.mapped("final_price")),
        }

    def action_refresh(self):
        self.write(self._compute_kpis())
        return {
            "type": "ir.actions.act_window",
            "res_model": "rawasi.dashboard.unified",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class RawasiNotificationHook(models.AbstractModel):
    _inherit = "rawasi.notification.hook"

    def _get_templates(self):
        templates = super()._get_templates()
        templates.update(
            {
                "internal_so_created": "أمر بيع داخلي أُنشئ: %(name)s",
                "internal_so_confirmed": "أمر بيع داخلي معتمد وبدأ التصنيع: %(name)s",
                "internal_delivered": "منتج تصنيع داخلي سُلِّم للمشروع: %(name)s",
            }
        )
        return templates
