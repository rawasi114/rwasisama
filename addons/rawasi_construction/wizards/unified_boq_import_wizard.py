# -*- coding: utf-8 -*-
"""معالج استيراد القاعدة الموحَّدة — ينشئ product.template مباشرة.

Stage B.2: تحوّل كامل لـ product.template كمنبع وحيد للحقيقة.

يستورد:
  • C (Exact Specs, 7 أوراق) — مكتبة بنود رئيسية → products
  • B (مكتبة الجاهزة) — صياغات «توريد وتركيب» → quotation_template

كل بند يدخل النظام يصبح product.template حقيقي في أودو:
  • is_construction_item=True
  • تحت product.category مناسبة (لا rawasi.unit، لا reference_item)
  • مع uom_id من uom.uom الأودوي
  • مع كل حقولنا المخصّصة (government_text, quotation_template,
    matching_keywords, rawasi_lcgpa_code_id, rawasi_delivery_type,
    rawasi_is_in_house, rawasi_workshop_type, pricing_rule/alert)
  • مع standard_price (تكلفة) و list_price (سعر)

إذا حُدِّدت competition_id → ينشئ أيضاً rawasi.boq.item مرتبط بالمنتج.
"""
import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.rawasi_construction.services.auto_normalization import (
    normalize_unit,
)

_logger = logging.getLogger(__name__)


_CONFIDENCE_MAP = {
    "عالية": 90.0, "متوسطة": 70.0, "منخفضة": 50.0,
    "high":   90.0, "medium":   70.0, "low":     50.0,
}

# خريطة الوحدات: من رمزنا الموحَّد → اسم uom.uom في أودو
_UOM_NAME_MAP = {
    "SQM": "m²",
    "CBM": "m³",
    "MTR": "m",
    "EA":  "Units",
    "KG":  "kg",
}


def _safe_get(row, idx):
    if idx >= len(row) or row[idx] is None:
        return None
    v = str(row[idx]).strip()
    return v if v else None


def _detect_workshop(text):
    if not text:
        return False, "none"
    t = text.strip().lower()
    if t in ("لا", "no", "false", "0", ""):
        return False, "none"
    if "نجار" in t or "خشب" in t or "carpent" in t:
        return True, "carpentry"
    if "حداد" in t or "معد" in t or "metal" in t:
        return True, "metalwork"
    if "ألمنيوم" in t or "المنيوم" in t or "alumin" in t:
        return True, "aluminum"
    if "cnc" in t:
        return True, "cnc"
    if t in ("نعم", "yes", "true", "1"):
        return True, "none"
    return False, "none"


def _detect_product_type(text):
    """يحوّل «نوع المنتج» إلى type القياسي."""
    if not text:
        return "consu"
    t = text.strip().lower()
    if "خدم" in t or "service" in t:
        return "service"
    return "consu"


class UnifiedBoqImportWizard(models.TransientModel):
    _name = "rawasi.unified.boq.import.wizard"
    _description = "معالج استيراد البنود الموحَّد (إلى product.template)"

    file_c = fields.Binary(
        string="ملف C (Exact Specs) أو القالب الموحَّد",
        required=True,
        help="ملف Excel: إما 7 أوراق (C الأصلي) أو القالب الموحَّد.",
    )
    filename_c = fields.Char()
    file_b = fields.Binary(string="ملف B (مكتبة الجاهزة — اختياري)")
    filename_b = fields.Char()

    competition_id = fields.Many2one(
        "rawasi.competition", string="ربط بمنافسة (اختياري)",
        help="إذا حُدِّدت، تُنشأ بنود BoQ على المنافسة مرتبطة بكل منتج.",
    )

    overwrite_existing = fields.Boolean(
        string="استبدال البنود الموجودة", default=False,
    )
    create_specifications = fields.Boolean(
        string="إنشاء المواصفات المُستخلَصة (ورقة 06)", default=True,
    )
    create_training_variants = fields.Boolean(
        string="إنشاء الصياغات البديلة (ورقة 02)", default=True,
    )

    # ════════ تنفيذ ════════
    def action_import(self):
        self.ensure_one()
        try:
            import openpyxl
        except ImportError:
            raise UserError(_("مكتبة openpyxl غير متوفّرة."))

        try:
            wb_c = openpyxl.load_workbook(
                io.BytesIO(base64.b64decode(self.file_c)), data_only=True,
            )
        except Exception as e:
            raise UserError(_("تعذّر فتح الملف الرئيسي: %s") % e)

        stats = {
            "products_created": 0,
            "products_updated": 0,
            "products_skipped": 0,
            "variants_created": 0,
            "specs_created": 0,
            "b_quotation_updated": 0,
            "b_products_created": 0,
            "b_matched_to_existing": 0,
            "boq_items_created": 0,
            "errors": [],
        }

        self._import_main_catalog(wb_c, stats)
        self._import_odoo_mapping(wb_c, stats)
        if self.create_training_variants:
            self._import_training_variants(wb_c, stats)
        if self.create_specifications:
            self._import_specifications(wb_c, stats)

        if self.file_b:
            try:
                wb_b = openpyxl.load_workbook(
                    io.BytesIO(base64.b64decode(self.file_b)), data_only=True,
                )
                self._import_file_b(wb_b, stats)
            except Exception as e:
                stats["errors"].append("فشل قراءة ملف B: %s" % e)

        return self._build_summary(stats)

    # ════════ Sheet 01 → products ════════
    def _import_main_catalog(self, wb, stats):
        sheet = self._find_sheet(wb, "دليل_البنود_الموحد", "01")
        if not sheet:
            stats["errors"].append("لم يُعثر على ورقة الكتالوج الرئيسي.")
            return
        ws = wb[sheet]
        Product = self.env["product.template"]

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            code = _safe_get(row, 0)
            if not code or not code.startswith("RSC."):
                continue
            name = _safe_get(row, 7)
            if not name:
                continue

            existing = Product.search([("reference_code", "=", code)], limit=1)
            if existing and not self.overwrite_existing:
                stats["products_skipped"] += 1
                if self.competition_id:
                    self._create_boq_line(existing, row, stats)
                continue

            vals = self._build_product_vals_from_C(row)
            if not vals:
                continue
            try:
                if existing:
                    existing.write(vals)
                    stats["products_updated"] += 1
                    product = existing
                else:
                    product = Product.create(vals)
                    stats["products_created"] += 1
                if self.competition_id:
                    self._create_boq_line(product, row, stats)
            except Exception as e:
                stats["errors"].append("سطر %d: %s" % (row_idx, e))

    def _build_product_vals_from_C(self, row):
        code = _safe_get(row, 0)
        name = _safe_get(row, 7)
        if not name:
            return None

        main_cat = _safe_get(row, 2) or "غير محدّد"
        unit_raw = _safe_get(row, 8)
        product_type = _detect_product_type(_safe_get(row, 9))
        is_in_house, workshop_type = _detect_workshop(_safe_get(row, 10))
        uom_id = self._lookup_uom(unit_raw)

        return {
            "name": name[:255],
            "default_code": code,
            "reference_code": code,
            "is_construction_item": True,
            "categ_id": self._lookup_or_create_category(main_cat),
            "uom_id": uom_id,
            "uom_po_id": uom_id,
            "type": product_type,
            "rawasi_delivery_type": "supply_and_install",
            "rawasi_is_in_house": is_in_house,
            "rawasi_workshop_type": workshop_type,
            "matching_keywords": _safe_get(row, 13),
            "rawasi_sample_specification": _safe_get(row, 16),
            "rawasi_pricing_rule": _safe_get(row, 19),
            "rawasi_pricing_alert": _safe_get(row, 20),
        }

    # ════════ Sheet 05 → تحديث مسار أودو ════════
    def _import_odoo_mapping(self, wb, stats):
        sheet = self._find_sheet(wb, "مسارات_أودو", "05")
        if not sheet:
            return
        ws = wb[sheet]
        Product = self.env["product.template"]

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            code = _safe_get(row, 0)
            if not code:
                continue
            product = Product.search([("reference_code", "=", code)], limit=1)
            if not product:
                continue
            vals = {}
            ptype = _detect_product_type(_safe_get(row, 3))
            if ptype != product.type:
                vals["type"] = ptype
            unit = self._lookup_uom(_safe_get(row, 4))
            if unit:
                vals.setdefault("uom_id", unit)
                vals.setdefault("uom_po_id", unit)
            is_ih, wt = _detect_workshop(_safe_get(row, 5))
            if is_ih:
                vals["rawasi_is_in_house"] = True
                vals["rawasi_workshop_type"] = wt
            if vals:
                product.write(vals)

    # ════════ Sheet 02 → صياغات تدريب على products ════════
    def _import_training_variants(self, wb, stats):
        sheet = self._find_sheet(wb, "خريطة_بنود_المشاريع", "02")
        if not sheet:
            return
        ws = wb[sheet]
        Product = self.env["product.template"]
        Variant = self.env["rawasi.item.variant"]

        from odoo.addons.rawasi_construction.models.rawasi_item_variant import (
            normalize_for_matching,
        )

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            original_text = _safe_get(row, 7)
            code = _safe_get(row, 11)
            if not original_text or not code:
                continue
            product = Product.search([("reference_code", "=", code)], limit=1)
            if not product:
                continue

            conf_text = _safe_get(row, 16)
            confidence = _CONFIDENCE_MAP.get((conf_text or "").lower(), 70.0)

            normalized = normalize_for_matching(original_text)
            if not normalized:
                continue
            existing = Variant.search([
                ("product_tmpl_id", "=", product.id),
                ("normalized_text", "=", normalized),
            ], limit=1)
            if existing:
                existing.write({
                    "frequency": existing.frequency + 1,
                    "last_seen_date": fields.Date.context_today(self),
                })
            else:
                Variant.create({
                    "product_tmpl_id": product.id,
                    "original_text": original_text[:255],
                    "frequency": 1,
                    "confidence_score": confidence,
                })
                stats["variants_created"] += 1

    # ════════ Sheet 06 → مواصفات دقيقة على products ════════
    def _import_specifications(self, wb, stats):
        sheet = self._find_sheet(wb, "مكتبة_المواصفات", "06")
        if not sheet:
            return
        ws = wb[sheet]
        Product = self.env["product.template"]
        Spec = self.env["rawasi.extracted.specification"]

        from odoo.addons.rawasi_construction.services.specifications_extractor import (
            extract_all as extract_specs,
        )

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            spec_text = _safe_get(row, 6)
            code = _safe_get(row, 8)
            if not spec_text or not code:
                continue
            product = Product.search([("reference_code", "=", code)], limit=1)
            if not product:
                continue
            extracted = extract_specs(spec_text)
            for key in ("dimensions", "thickness", "diameter", "strength"):
                value = extracted.get(key)
                if not value:
                    continue
                existing = Spec.search([
                    ("product_tmpl_id", "=", product.id),
                    ("spec_key", "=", key),
                    ("spec_value", "=", value),
                ], limit=1)
                if existing:
                    continue
                Spec.create({
                    "product_tmpl_id": product.id,
                    "spec_key": key,
                    "spec_value": str(value)[:255],
                    "extracted_via_auto": True,
                })
                stats["specs_created"] += 1

    # ════════ ملف B → quotation_template على products ════════
    def _import_file_b(self, wb, stats):
        sheet = None
        for sh in wb.sheetnames:
            if "مكتبة" in sh or "البنود" in sh:
                sheet = sh
                break
        if not sheet:
            sheet = wb.sheetnames[0]
        ws = wb[sheet]
        Product = self.env["product.template"]

        header_idx = None
        for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row and any(str(c or "").strip() == "كود البند" for c in row):
                header_idx = i
                break
        if header_idx is None:
            stats["errors"].append("ملف B: لم يُعثر على صف الرأس.")
            return

        b_seq = 800
        current_group_name = None

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx <= header_idx:
                continue
            if not row or not any(row):
                continue

            grp_code = _safe_get(row, 1)
            grp_name = _safe_get(row, 2)
            if grp_name:
                current_group_name = grp_name

            item_text = _safe_get(row, 4)
            if not item_text or len(item_text) < 15:
                continue

            unit_raw = _safe_get(row, 5)
            lcgpa_raw = _safe_get(row, 6)
            lcgpa_id = False
            if lcgpa_raw:
                lc = self.env["rawasi.lcgpa.code"].search(
                    [("code", "=", lcgpa_raw)], limit=1)
                lcgpa_id = lc.id if lc else False

            # حاول مطابقة B مع منتج موجود
            approved_name = item_text[:80]
            matched = Product.search([
                ("is_construction_item", "=", True),
                ("name", "ilike", approved_name[:30]),
            ], limit=1)

            if matched:
                if not matched.quotation_template:
                    matched.quotation_template = "<p>%s</p>" % item_text
                    stats["b_quotation_updated"] += 1
                stats["b_matched_to_existing"] += 1
                continue

            group_num = (grp_code or "00").strip()
            if not group_num.isdigit() or len(group_num) > 2:
                group_num = "99"
            else:
                group_num = group_num.zfill(2)
            synthesized_code = "RSC.%s.00.00.%03d" % (group_num, b_seq)
            while Product.search_count([("reference_code", "=", synthesized_code)]):
                b_seq += 1
                synthesized_code = "RSC.%s.00.00.%03d" % (group_num, b_seq)

            uom_id = self._lookup_uom(unit_raw)
            try:
                Product.create({
                    "name": approved_name,
                    "default_code": synthesized_code,
                    "reference_code": synthesized_code,
                    "is_construction_item": True,
                    "categ_id": self._lookup_or_create_category(
                        current_group_name or "غير محدّد"
                    ),
                    "uom_id": uom_id,
                    "uom_po_id": uom_id,
                    "type": "consu",
                    "rawasi_delivery_type": "supply_and_install",
                    "rawasi_lcgpa_code_id": lcgpa_id,
                    "quotation_template": "<p>%s</p>" % item_text,
                })
                stats["b_products_created"] += 1
                b_seq += 1
            except Exception as e:
                stats["errors"].append("B سطر %d: %s" % (row_idx, e))

    # ════════ سطر BoQ مرتبط بمنتج ════════
    def _create_boq_line(self, product, row, stats):
        if not self.competition_id:
            return
        try:
            qty = float(_safe_get(row, 11) or 1.0)
        except (ValueError, TypeError):
            qty = 1.0
        # نحاول قراءة التكلفة والسعر من أي عمود مناسب
        unit_cost = product.standard_price
        unit_price = product.list_price
        try:
            self.env["rawasi.boq.item"].create({
                "competition_id": self.competition_id.id,
                "name": product.name,
                "product_tmpl_id": product.id,
                "quantity": qty,
                "unit_cost": unit_cost,
                "unit_price": unit_price,
                "lcgpa_code_id": product.rawasi_lcgpa_code_id.id,
                "sbc_code_id": product.rawasi_sbc_code_id.id,
            })
            stats["boq_items_created"] += 1
        except Exception as e:
            stats["errors"].append("BoQ line %s: %s" % (product.name[:20], e))

    # ════════ مساعدات ════════
    def _find_sheet(self, wb, contains, prefix):
        for sh in wb.sheetnames:
            if contains in sh or sh.startswith(prefix):
                return sh
        return None

    def _lookup_or_create_category(self, name):
        Category = self.env["product.category"]
        root = self.env.ref(
            "rawasi_construction.cat_rawasi_root",
            raise_if_not_found=False,
        )
        if not name:
            return root.id if root else False
        cat = Category.search([("name", "=", name)], limit=1)
        if cat:
            return cat.id
        cat = Category.search([("name", "ilike", name[:30])], limit=1)
        if cat:
            return cat.id
        return Category.create({
            "name": name[:64],
            "parent_id": root.id if root else False,
        }).id

    def _lookup_uom(self, unit_raw):
        if not unit_raw:
            return self.env.ref("uom.product_uom_unit").id
        Uom = self.env["uom.uom"]
        uom = Uom.search([("name", "=", unit_raw)], limit=1)
        if uom:
            return uom.id
        code, _label = normalize_unit(unit_raw)
        if code:
            mapped_name = _UOM_NAME_MAP.get(code)
            if mapped_name:
                uom = Uom.search([("name", "=", mapped_name)], limit=1)
                if uom:
                    return uom.id
        return self.env.ref("uom.product_uom_unit").id

    def _build_summary(self, stats):
        total = stats["products_created"] + stats["b_products_created"]
        msg = _(
            "اكتمل استيراد البنود إلى product.template:\n\n"
            "── ملف C ──\n"
            "  • منتجات أُنشئت: %(products_created)d\n"
            "  • منتجات حُدِّثت: %(products_updated)d\n"
            "  • منتجات تخطّيتها: %(products_skipped)d\n"
            "  • صياغات تدريبية: %(variants_created)d\n"
            "  • مواصفات دقيقة: %(specs_created)d\n\n"
            "── ملف B ──\n"
            "  • صياغات «توريد وتركيب»: %(b_quotation_updated)d\n"
            "  • بنود مطابقة: %(b_matched_to_existing)d\n"
            "  • منتجات جديدة من B: %(b_products_created)d\n\n"
            "── المنافسة ──\n"
            "  • بنود BoQ أُنشئت: %(boq_items_created)d\n\n"
            "إجمالي المنتجات الفاعلة: ≈ %(total)d\n\n%(errors_section)s"
        ) % {
            **stats, "total": total,
            "errors_section": (
                _("تحذيرات (%d):\n%s") % (
                    len(stats["errors"]),
                    "\n".join("  • " + e for e in stats["errors"][:20]),
                )
            ) if stats["errors"] else _("لا توجد أخطاء."),
        }
        _logger.info("Unified BOQ import done: %s", stats)

        return {
            "type": "ir.actions.act_window",
            "name": _("بنود المقاولات (المنتجات)"),
            "res_model": "product.template",
            "view_mode": "list,form",
            "domain": [("is_construction_item", "=", True)],
            "context": {"search_default_construction_only": 1},
            "help": "<pre>" + msg + "</pre>",
        }
