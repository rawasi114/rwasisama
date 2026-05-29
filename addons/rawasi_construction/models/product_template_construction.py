# -*- coding: utf-8 -*-
"""تخصيص product.template لاحتياجات بنود المقاولات.

كل بند في النظام يصبح منتج أودو حقيقي → يربط بـ:
  • المخزون (Stock) — تتبّع كميات وحركات
  • المشتريات (Purchase) — موردون وأسعار تاريخية
  • المبيعات (Sale) — عروض السعر
  • التصنيع (MRP) — قائمة مواد لكل بند يُصنَّع داخلياً
  • المحاسبة — قيود تلقائية للمخزون والمصاريف
"""
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ── علم البند الإنشائي ─────────────────────────────────────
    is_construction_item = fields.Boolean(
        string="بند مقاولات",
        default=False, index=True,
        help="يميّز البند كبند مقاولات يخضع لمنظومة رواسي سما "
             "(يظهر في قائمة «بنود المقاولات» وفي wizard البنود الموحَّدة).",
    )

    # ── الكود المرجعي الموحَّد ─────────────────────────────────
    reference_code = fields.Char(
        string="الرمز المرجعي الموحَّد",
        index=True, copy=False,
        help="نمط: RSC.XX.YY.ZZ.NNN — يُستخدم في منظومة المطابقة وتجمع الأسعار.",
    )

    # ── الأوصاف ───────────────────────────────────────────────
    government_text = fields.Text(
        string="الوصف الكامل من الجهة",
        translate=True,
        help="النص كاملاً كما ورد في جدول كميات الجهة الحكومية. "
             "يُعبَّأ آلياً عند أول مطابقة، يبقى مرجعاً للعقود.",
    )
    quotation_template = fields.Html(
        string="صياغة عرض السعر (توريد وتركيب)",
        translate=True, sanitize=True,
        help="صياغة احترافية مختصرة جاهزة للنسخ في عرض السعر.",
    )

    # ── دعم منظومة المطابقة الذكية ────────────────────────────
    matching_keywords = fields.Char(
        string="كلمات المطابقة",
        help="مرادفات مفصولة بفواصل تغذّي matching_engine — "
             "مثال: «بورسلين، porcelain، 60x60، أرضيات».",
    )

    # ── الربط بالأكواد الإنشائية ──────────────────────────────
    rawasi_lcgpa_code_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA",
        index=True,
    )
    rawasi_sbc_code_id = fields.Many2one(
        "rawasi.sbc.code", string="رمز SBC",
    )

    # ── خصائص التصنيع الداخلي ─────────────────────────────────
    rawasi_is_in_house = fields.Boolean(
        string="يُصنَّع في ورشة رواسي",
        default=False, index=True,
        help="إذا فُعِّل، يتطلب البند قائمة مواد (BoM) ويُدار من rwasi_workshop.",
    )
    rawasi_workshop_type = fields.Selection(
        [
            ("carpentry", "نجارة"),
            ("metalwork", "حدادة"),
            ("aluminum",  "ألمنيوم"),
            ("cnc",       "CNC"),
            ("none",      "لا يُصنَّع داخلياً"),
        ],
        default="none", string="نوع الورشة",
    )

    # ── قواعد التسعير ─────────────────────────────────────────
    rawasi_pricing_rule = fields.Text(string="قاعدة التسعير الداخلية")
    rawasi_pricing_alert = fields.Text(string="تنبيه التسعير")
    rawasi_sample_specification = fields.Text(string="نموذج مواصفة مرجعية")

    # ── الهرمية النصية (للبحث السريع — مكمّل لـ categ_id) ─────
    rawasi_main_category_text = fields.Char(
        string="الفئة الرئيسية (نص)",
        compute="_compute_rawasi_hierarchy_text", store=True,
        help="مُشتقّ من categ_id لتسهيل البحث النصي.",
    )

    # ── العدّادات الذكية ──────────────────────────────────────
    rawasi_bom_count = fields.Integer(
        string="عدد قوائم المواد", compute="_compute_rawasi_bom_count",
    )
    rawasi_boq_line_count = fields.Integer(
        string="مرات الاستخدام في جداول الكميات",
        compute="_compute_rawasi_boq_line_count",
    )

    @api.depends("categ_id", "categ_id.parent_id")
    def _compute_rawasi_hierarchy_text(self):
        for rec in self:
            cat = rec.categ_id
            if not cat:
                rec.rawasi_main_category_text = False
                continue
            root = cat
            while root.parent_id:
                root = root.parent_id
            rec.rawasi_main_category_text = root.name or False

    def _compute_rawasi_bom_count(self):
        BoM = self.env["mrp.bom"]
        for rec in self:
            rec.rawasi_bom_count = BoM.search_count(
                [("product_tmpl_id", "=", rec.id)]
            )

    def _compute_rawasi_boq_line_count(self):
        BoQ = self.env["rawasi.boq.item"]
        for rec in self:
            # رابطنا (لو موجود) — في Stage B سنضيف product_template_id
            rec.rawasi_boq_line_count = 0

    # ── الإجراءات ─────────────────────────────────────────────
    def action_view_boms(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("قوائم مواد %s") % self.name,
            "res_model": "mrp.bom",
            "view_mode": "list,form",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {"default_product_tmpl_id": self.id},
        }

    def action_create_default_bom(self):
        """ينشئ قائمة مواد فارغة افتراضية لبنود الورشة."""
        self.ensure_one()
        if not self.rawasi_is_in_house:
            return False
        BoM = self.env["mrp.bom"]
        existing = BoM.search([("product_tmpl_id", "=", self.id)], limit=1)
        if existing:
            return {
                "type": "ir.actions.act_window",
                "res_model": "mrp.bom",
                "res_id": existing.id,
                "view_mode": "form",
            }
        bom = BoM.create({
            "product_tmpl_id": self.id,
            "product_qty": 1.0,
            "type": "normal",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.bom",
            "res_id": bom.id,
            "view_mode": "form",
        }

    @api.model_create_multi
    def create(self, vals_list):
        # افتراض ذكي: لو is_construction_item بدون نوع، اضبط النوع كمنتج
        # ولو بدون فئة، اضبطها على جذر «بنود المقاولات»
        default_root_cat = self.env.ref(
            "rawasi_construction.cat_rawasi_root", raise_if_not_found=False
        )
        for vals in vals_list:
            if vals.get("is_construction_item"):
                if not vals.get("type"):
                    vals["type"] = "consu"
                if not vals.get("categ_id") and default_root_cat:
                    vals["categ_id"] = default_root_cat.id
        records = super().create(vals_list)
        # ننشئ BoM فارغة لبنود الورشة تلقائياً
        for rec in records:
            if rec.rawasi_is_in_house and rec.is_construction_item:
                self.env["mrp.bom"].create({
                    "product_tmpl_id": rec.id,
                    "product_qty": 1.0,
                    "type": "normal",
                })
        return records
