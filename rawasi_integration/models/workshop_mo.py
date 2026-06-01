# -*- coding: utf-8 -*-
from odoo import fields, models


class RawasiWorkshopMo(models.Model):
    """يربط أمر التصنيع بأمر التصنيع الداخلي ويُضيف التسليم التلقائي للمشروع."""

    _inherit = "rawasi.workshop.mo"

    internal_workshop_order_id = fields.Many2one(
        "rawasi.internal.workshop.order",
        string="أمر التصنيع الداخلي",
        copy=False,
        help="إن وُجد، فإن هذا الأمر ناتج عن تصنيع داخلي لمشروع مقاولات.",
    )

    def action_done(self):
        res = super().action_done()
        for mo in self:
            if mo.internal_workshop_order_id:
                mo._deliver_to_construction_project()
        return res

    def _deliver_to_construction_project(self):
        """ينقل المنتج التام لمخزن المشروع (إن توفّر) ويقفل طلب مواد المقاولات الأصلي."""
        self.ensure_one()
        iwo = self.internal_workshop_order_id
        # محاولة نقل مخزني داخلي إن توفّرت المواقع
        self._try_internal_transfer(iwo)
        # قفل طلب مواد المقاولات الأصلي (يصبح مكتملاً)
        mr = iwo.construction_mr_id
        if mr and mr.state not in ("issued", "cancelled"):
            mr.sudo().write(
                {
                    "state": "issued",
                    "issuer_user_id": self.env.uid,
                    "issue_date": fields.Datetime.now(),
                }
            )
        iwo.state = "delivered_to_project"
        # تسجيل تدقيق + إشعار
        self.env["rawasi.audit.trail"].log(
            iwo,
            "issue",
            detail="تسليم منتج تصنيع داخلي للمشروع %s" % (iwo.project_id.display_name or ""),
        )
        self.env["rawasi.notification.hook"].send(iwo, "internal_delivered")

    def _try_internal_transfer(self, iwo):
        """نقل اختياري: من موقع إنتاج القسم إلى المخزن الرئيسي للمشروع."""
        self.ensure_one()
        project = iwo.project_id
        dest = project.rawasi_main_location_id if project else False
        src = self.section_id.production_location_id
        if not (dest and src):
            return False
        moves = []
        for line in self.product_line_ids:
            if not line.product_id:
                continue
            moves.append(
                (
                    0,
                    0,
                    {
                        "name": line.description or line.product_id.display_name,
                        "product_id": line.product_id.id,
                        "product_uom_qty": line.qty,
                        "product_uom": line.uom_id.id,
                        "location_id": src.id,
                        "location_dest_id": dest.id,
                    },
                )
            )
        if not moves:
            return False
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )
        picking_type = warehouse.int_type_id if warehouse else False
        if not picking_type:
            return False
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "origin": "%s ← %s" % (project.display_name, self.name),
                "move_ids": moves,
            }
        )
        return picking
