# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError


class RawasiMaterialRequest(models.Model):
    """يضيف زر «تصنيع داخلي بالورشة» لطلب مواد المقاولات."""

    _inherit = "rawasi.material.request"

    def action_internal_workshop_quote(self):
        """ينشئ أمر تصنيع داخلي لبند BoQ بمسار in_house_workshop."""
        self.ensure_one()
        if self.procurement_type != "in_house_workshop":
            raise UserError("هذا البند ليس بمسار «تصنيع داخلي بالورشة».")
        if self.state != "approved_budget":
            raise UserError("يجب اعتماد الميزانية أولاً قبل التصنيع الداخلي.")
        existing = self.env["rawasi.internal.workshop.order"].search(
            [("construction_mr_id", "=", self.id), ("state", "!=", "cancelled")], limit=1
        )
        if existing:
            return existing._action_open()

        boq = self.boq_item_id
        qty = boq.qty if boq else 1.0
        cost = (boq.reference_item_id.standard_cost if boq and boq.reference_item_id else 0.0) * qty
        section = self._guess_workshop_section(boq)
        order = self.env["rawasi.internal.workshop.order"].create(
            {
                "construction_mr_id": self.id,
                "section_id": section.id if section else False,
                "qty": qty,
                "cost_estimate": cost,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "تصنيع داخلي بالورشة",
            "res_model": "rawasi.internal.workshop.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "new",
        }

    def _guess_workshop_section(self, boq):
        """يخمّن القسم من تصنيف البند المرجعي (نجارة/حدادة)، وإلا أول قسم."""
        Section = self.env["rawasi.workshop.section"]
        category = boq.reference_item_id.category if boq and boq.reference_item_id else False
        code_map = {"carpentry": "CARP", "steel": "STEEL", "aluminum": "STEEL"}
        code = code_map.get(category)
        if code:
            sec = Section.search([("code", "=", code)], limit=1)
            if sec:
                return sec
        return Section.search([], limit=1)
