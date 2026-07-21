# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    """امتداد purchase.order القياسي لربطه بطلب مواد المقاولات.

    عند رفع مهندس الموقع طلب مواد (action_submit)، يُنشأ تلقائياً
    purchase.order بحالة 'draft' (= RFQ) بكل سطور المواد، ويُربط بـ MR
    عبر rawasi_mr_id. قسم المشتريات يحلّ المورّد الافتراضي بمورّد فعلي
    ثم يؤكّد الـ RFQ.
    """
    _inherit = "purchase.order"

    rawasi_mr_id = fields.Many2one(
        "rawasi.material.request",
        string="طلب مواد رواسي",
        readonly=True, copy=False, index=True,
        help="طلب المواد الذي تَولَّد منه هذا الـ RFQ تلقائياً.",
    )
    rawasi_project_id = fields.Many2one(
        related="rawasi_mr_id.project_id",
        string="مشروع رواسي",
        store=True, readonly=True,
    )
