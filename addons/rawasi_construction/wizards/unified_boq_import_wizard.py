# -*- coding: utf-8 -*-
"""معالج استيراد القاعدة الموحَّدة للبنود — Unified BOQ Library Wizard.

يستورد ~330 بند مرجعي معتمَد دفعة واحدة من ملفين:

  ① ملف C (Exact Specs) — إلزامي
     يحوي 7 أوراق:
       01_دليل_البنود_الموحد        → reference_item (254 سجل)
       02_خريطة_بنود_المشاريع       → item_variant + audit_trail (408 تدريب)
       05_مسارات_أودو_المقترحة      → product_type/unit/workshop mapping
       06_مكتبة_المواصفات_الدقيقة   → extracted_specification (408 سجل)

  ② ملف B (مكتبة البنود الجاهزة) — اختياري
     يحوي 200 بند بصياغة «توريد وتركيب» جاهزة:
       - يُكمل quotation_template للبنود المتقاطعة مع C
       - يُضيف ~76 بنداً متخصّصاً ناقصاً (مطارات/مساجد/موانئ/شبكات)

عملية لمرة واحدة في حياة الشركة — بعدها كل BoQ جديد يمرّ على wizard
الاستيراد العادي مع نسبة ربط متوقعة 75-85% من أول لقطة.
"""
import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.rawasi_construction.services.auto_normalization import (
    normalize_unit,
)
from odoo.addons.rawasi_construction.services.specifications_extractor import (
    extract_all as extract_specs,
)
from odoo.addons.rawasi_construction.models.rawasi_item_variant import (
    normalize_for_matching,
)

_logger = logging.getLogger(__name__)


# ── الحدود الفاصلة لمطابقة B مع C ────────────────────────────────
_B_MATCH_THRESHOLD = 75.0   # ≥ 75% → نحدّث quotation_template على البند الموجود
                            # < 75% → ننشئ بنداً جديداً من B

_CONFIDENCE_MAP = {
    "عالية": 90.0, "متوسطة": 70.0, "منخفضة": 50.0,
    "high":   90.0, "medium":   70.0, "low":     50.0,
}


def _safe_get(row, idx):
    if idx >= len(row) or row[idx] is None:
        return None
    v = str(row[idx]).strip()
    return v if v else None


def _detect_workshop(text):
    """يحوّل نص «ارتباط بورش رواسي» إلى (is_in_house, workshop_type)."""
    if not text:
        return False, "none"
    t = text.strip().lower()
    if t in ("لا", "no", "false", "0", ""):
        return False, "none"
    # كلمات مفتاحية للورش
    if "نجار" in t or "خشب" in t or "carpent" in t:
        return True, "carpentry"
    if "حداد" in t or "معد" in t or "metal" in t:
        return True, "metalwork"
    if "ألمنيوم" in t or "المنيوم" in t or "alumin" in t:
        return True, "aluminum"
    if "cnc" in t:
        return True, "cnc"
    # نعم/yes بدون تخصيص نوع → ندَع none لكن نفعّل العَلَم
    if t in ("نعم", "yes", "true", "1"):
        return True, "none"
    return False, "none"


def _detect_product_type(text):
    """يحوّل «نوع المنتج» إلى product_type_odoo."""
    if not text:
        return "product"
    t = text.strip().lower()
    if "خدم" in t or "service" in t:
        return "service"
    if "توريد وخدم" in t or "combined" in t:
        return "combined"
    return "product"


class UnifiedBoqImportWizard(models.TransientModel):
    _name = "rawasi.unified.boq.import.wizard"
    _description = "معالج استيراد القاعدة الموحَّدة (C+B)"

    file_c = fields.Binary(
        string="ملف C (Exact Specs)", required=True,
        help="ملف Excel يحوي 7 أوراق — الأساس الذكي للقاعدة.",
    )
    filename_c = fields.Char()
    file_b = fields.Binary(
        string="ملف B (مكتبة البنود الجاهزة)",
        help="اختياري — يضيف صياغة «توريد وتركيب» والبنود المتخصّصة.",
    )
    filename_b = fields.Char()
    overwrite_existing = fields.Boolean(
        string="استبدال البنود الموجودة",
        default=False,
        help="إذا كان البند المرجعي موجوداً (بنفس الكود)، يُكتب فوقه بدل التخطي.",
    )
    create_specifications = fields.Boolean(
        string="إنشاء المواصفات المُستخلَصة (ورقة 06)",
        default=True,
    )
    create_training_variants = fields.Boolean(
        string="إنشاء الصياغات البديلة من خريطة المشاريع (ورقة 02)",
        default=True,
    )

    # ════════ تنفيذ الاستيراد ════════
    def action_import(self):
        self.ensure_one()
        try:
            import openpyxl
        except ImportError:
            raise UserError(_("مكتبة openpyxl غير متوفّرة على الخادم."))

        try:
            wb_c = openpyxl.load_workbook(
                io.BytesIO(base64.b64decode(self.file_c)),
                data_only=True,
            )
        except Exception as e:
            raise UserError(_("تعذّر فتح ملف C: %s") % e)

        stats = {
            "c_items_created": 0,
            "c_items_updated": 0,
            "c_items_skipped": 0,
            "c_odoo_mapping_updated": 0,
            "c_variants_created": 0,
            "c_specs_created": 0,
            "b_quotation_updated": 0,
            "b_items_created": 0,
            "b_items_matched_to_c": 0,
            "errors": [],
        }

        # ── المسار الأول: ورقة 01 (البنود الموحَّدة) ───────────────
        self._import_sheet_01(wb_c, stats)

        # ── المسار الثاني: ورقة 05 (مسارات أودو) ────────────────────
        self._import_sheet_05(wb_c, stats)

        # ── المسار الثالث: ورقة 02 (تدريب — صياغات بديلة) ───────────
        if self.create_training_variants:
            self._import_sheet_02(wb_c, stats)

        # ── المسار الرابع: ورقة 06 (مواصفات دقيقة) ─────────────────
        if self.create_specifications:
            self._import_sheet_06(wb_c, stats)

        # ── المسار الخامس: ملف B (اختياري) ──────────────────────────
        if self.file_b:
            try:
                wb_b = openpyxl.load_workbook(
                    io.BytesIO(base64.b64decode(self.file_b)),
                    data_only=True,
                )
                self._import_file_b(wb_b, stats)
            except Exception as e:
                stats["errors"].append("فشل قراءة ملف B: %s" % e)

        return self._build_summary_action(stats)

    # ════════ Sheet 01: البنود الموحَّدة ════════
    def _import_sheet_01(self, wb, stats):
        sheet_name = self._find_sheet(wb, "دليل_البنود_الموحد", "01")
        if not sheet_name:
            stats["errors"].append("لم يُعثر على ورقة «دليل البنود الموحَّد».")
            return
        ws = wb[sheet_name]
        RefItem = self.env["rawasi.reference.item"]

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:  # رأس
                continue
            code = _safe_get(row, 0)
            if not code or not code.startswith("RSC."):
                continue

            existing = RefItem.search([("reference_code", "=", code)], limit=1)
            if existing and not self.overwrite_existing:
                stats["c_items_skipped"] += 1
                continue

            vals = self._build_vals_from_sheet_01(row)
            if not vals:
                continue
            try:
                if existing:
                    existing.write(vals)
                    stats["c_items_updated"] += 1
                else:
                    RefItem.create(vals)
                    stats["c_items_created"] += 1
            except Exception as e:
                stats["errors"].append("سطر %d: %s" % (row_idx, e))

    def _build_vals_from_sheet_01(self, row):
        code = _safe_get(row, 0)
        approved_name = _safe_get(row, 7)
        if not approved_name:
            return None

        unit_raw = _safe_get(row, 8)
        unit_id = self._lookup_unit(unit_raw)

        product_type = _detect_product_type(_safe_get(row, 9))
        is_in_house, workshop_type = _detect_workshop(_safe_get(row, 10))

        return {
            "reference_code": code,
            "approved_name": (approved_name or "")[:255],
            "main_category": (_safe_get(row, 2) or "غير محدّد")[:255],
            "item_group": (_safe_get(row, 4) or "غير محدّد")[:255],
            "simplified_desc": (_safe_get(row, 6) or "")[:255] or False,
            "default_uom_id": unit_id,
            "product_type_odoo": product_type,
            "is_in_house": is_in_house,
            "workshop_type": workshop_type,
            "matching_keywords": _safe_get(row, 13),
            "sample_specification": _safe_get(row, 16),
            "pricing_rule": _safe_get(row, 19),
            "pricing_alert": _safe_get(row, 20),
            "review_status": "approved",
            "created_via": "bulk_import",
        }

    # ════════ Sheet 05: مسارات أودو ════════
    def _import_sheet_05(self, wb, stats):
        sheet_name = self._find_sheet(wb, "مسارات_أودو", "05")
        if not sheet_name:
            return
        ws = wb[sheet_name]
        RefItem = self.env["rawasi.reference.item"]

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            code = _safe_get(row, 0)
            if not code:
                continue
            item = RefItem.search([("reference_code", "=", code)], limit=1)
            if not item:
                continue

            vals = {}
            ptype = _detect_product_type(_safe_get(row, 3))
            if ptype != "product":  # ما نكتب الافتراضي
                vals["product_type_odoo"] = ptype
            unit = self._lookup_unit(_safe_get(row, 4))
            if unit and not item.default_uom_id:
                vals["default_uom_id"] = unit
            is_ih, wt = _detect_workshop(_safe_get(row, 5))
            if is_ih:
                vals["is_in_house"] = True
                vals["workshop_type"] = wt
            if vals:
                item.write(vals)
                stats["c_odoo_mapping_updated"] += 1

    # ════════ Sheet 02: تدريب الذكاء (variants + audit) ════════
    def _import_sheet_02(self, wb, stats):
        sheet_name = self._find_sheet(wb, "خريطة_بنود_المشاريع", "02")
        if not sheet_name:
            return
        ws = wb[sheet_name]
        RefItem = self.env["rawasi.reference.item"]
        Variant = self.env["rawasi.item.variant"]
        Audit = self.env["rawasi.audit.trail"]

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            original_text = _safe_get(row, 7)
            code = _safe_get(row, 11)
            if not original_text or not code:
                continue

            ref = RefItem.search([("reference_code", "=", code)], limit=1)
            if not ref:
                continue

            # confidence: عمود 17 رقمي، 16 نصي
            conf_text = _safe_get(row, 16)
            conf_num = None
            try:
                conf_num = float(row[17]) if len(row) > 17 and row[17] else None
            except (ValueError, TypeError):
                conf_num = None
            confidence = conf_num if conf_num is not None else _CONFIDENCE_MAP.get(
                (conf_text or "").lower(), 70.0
            )

            # variant
            normalized = normalize_for_matching(original_text)
            if normalized:
                existing_var = Variant.search([
                    ("reference_item_id", "=", ref.id),
                    ("normalized_text", "=", normalized),
                ], limit=1)
                if existing_var:
                    existing_var.write({
                        "frequency": existing_var.frequency + 1,
                        "last_seen_date": fields.Date.context_today(self),
                    })
                else:
                    Variant.create({
                        "reference_item_id": ref.id,
                        "original_text": original_text[:255],
                        "frequency": 1,
                        "confidence_score": confidence,
                    })
                    stats["c_variants_created"] += 1

            # audit trail
            Audit.create({
                "original_text": original_text,
                "reference_item_id": ref.id,
                "match_source": "manual",
                "confidence_score": confidence,
                "user_action": "accepted",
                "notes": "[TRAINING_DATA] استيراد من ورقة 02 خريطة بنود المشاريع",
            })

    # ════════ Sheet 06: المواصفات الدقيقة ════════
    def _import_sheet_06(self, wb, stats):
        sheet_name = self._find_sheet(wb, "مكتبة_المواصفات", "06")
        if not sheet_name:
            return
        ws = wb[sheet_name]
        RefItem = self.env["rawasi.reference.item"]
        Spec = self.env["rawasi.extracted.specification"]

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                continue
            spec_text = _safe_get(row, 6)
            code = _safe_get(row, 8)
            if not spec_text or not code:
                continue

            ref = RefItem.search([("reference_code", "=", code)], limit=1)
            if not ref:
                continue

            extracted = extract_specs(spec_text)
            for key in ("dimensions", "thickness", "diameter", "strength"):
                value = extracted.get(key)
                if not value:
                    continue
                # تفادي التكرار
                existing = Spec.search([
                    ("reference_item_id", "=", ref.id),
                    ("spec_key", "=", key),
                    ("spec_value", "=", value),
                ], limit=1)
                if existing:
                    continue
                Spec.create({
                    "reference_item_id": ref.id,
                    "spec_key": key,
                    "spec_value": str(value)[:255],
                    "extracted_via_auto": True,
                })
                stats["c_specs_created"] += 1

    # ════════ File B: مكتبة البنود الجاهزة ════════
    def _import_file_b(self, wb, stats):
        # نبحث عن الورقة الرئيسية
        sheet_name = None
        for sh in wb.sheetnames:
            if "مكتبة" in sh or "البنود" in sh:
                sheet_name = sh
                break
        if not sheet_name:
            sheet_name = wb.sheetnames[0]
        ws = wb[sheet_name]

        RefItem = self.env["rawasi.reference.item"]

        # ابحث عن صف الرأس
        header_idx = None
        for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row and any(
                str(c or "").strip() in ("كود البند", "المستوى 1 (المجموعة)")
                for c in row
            ):
                header_idx = i
                break
        if header_idx is None:
            stats["errors"].append("ملف B: لم يُعثر على صف الرأس.")
            return

        b_seq = 800  # رقم تسلسلي ابتدائي لبنود B التي لم تجد ربطاً في C
        current_group_code = None
        current_group_name = None

        for row_idx, row in enumerate(
            ws.iter_rows(values_only=True), start=1
        ):
            if row_idx <= header_idx:
                continue
            if not row or not any(row):
                continue

            # forward-fill للمجموعة
            grp_code = _safe_get(row, 1)
            grp_name = _safe_get(row, 2)
            if grp_code:
                current_group_code = grp_code
            if grp_name:
                current_group_name = grp_name

            item_text = _safe_get(row, 4)  # المستوى 4 — الوصف الكامل
            if not item_text or len(item_text) < 15:
                continue

            unit_raw = _safe_get(row, 5)
            unit_id = self._lookup_unit(unit_raw)
            lcgpa_raw = _safe_get(row, 6)
            lcgpa_id = False
            if lcgpa_raw:
                lc = self.env["rawasi.lcgpa.code"].search(
                    [("code", "=", lcgpa_raw)], limit=1,
                )
                lcgpa_id = lc.id if lc else False

            # ① حاول مطابقة B مع بند C موجود
            try:
                from odoo.addons.rawasi_construction.services.matching_engine import (
                    find_match,
                )
                ref, conf, _src = find_match(
                    self.env, item_text,
                    lcgpa_raw=lcgpa_raw,
                )
            except Exception:
                ref, conf = False, 0.0

            if ref and conf >= _B_MATCH_THRESHOLD:
                # حدّث الصياغة الجاهزة على البند الموجود
                if not ref.quotation_template:
                    ref.quotation_template = "<p>%s</p>" % item_text
                    stats["b_quotation_updated"] += 1
                stats["b_items_matched_to_c"] += 1
                continue

            # ② ما لقي → أنشئ بند جديد بكود مُولَّد
            group_num = (current_group_code or "00").strip()
            if not group_num.isdigit() or len(group_num) > 2:
                group_num = "99"
            else:
                group_num = group_num.zfill(2)

            synthesized_code = "RSC.%s.00.00.%03d" % (group_num, b_seq)
            while RefItem.search_count([("reference_code", "=", synthesized_code)]):
                b_seq += 1
                synthesized_code = "RSC.%s.00.00.%03d" % (group_num, b_seq)

            approved_name = item_text[:80]
            level2 = _safe_get(row, 2) or current_group_name or "غير محدّد"
            level3 = _safe_get(row, 3) or "غير محدّد"

            try:
                RefItem.create({
                    "reference_code": synthesized_code,
                    "approved_name": approved_name,
                    "main_category": current_group_name or "غير محدّد",
                    "item_group": level2[:255],
                    "simplified_desc": level3[:255],
                    "default_uom_id": unit_id,
                    "lcgpa_code_id": lcgpa_id,
                    "quotation_template": "<p>%s</p>" % item_text,
                    "review_status": "approved",
                    "created_via": "bulk_import",
                })
                stats["b_items_created"] += 1
                b_seq += 1
            except Exception as e:
                stats["errors"].append("B سطر %d: %s" % (row_idx, e))

    # ════════ مساعدات ════════
    def _find_sheet(self, wb, contains, prefix):
        for sh in wb.sheetnames:
            if contains in sh or sh.startswith(prefix):
                return sh
        return None

    def _lookup_unit(self, unit_raw):
        """يبحث عن وحدة قياس بأي صياغة عبر normalize_unit."""
        if not unit_raw:
            return False
        code, _label = normalize_unit(unit_raw)
        if not code:
            return False
        unit = self.env["rawasi.unit"].search([("code", "=", code)], limit=1)
        return unit.id if unit else False

    def _build_summary_action(self, stats):
        total_created = stats["c_items_created"] + stats["b_items_created"]
        msg = _(
            "اكتمل استيراد القاعدة الموحَّدة:\n\n"
            "── ملف C ──\n"
            "  • بنود مرجعية أُنشئت: %(c_items_created)d\n"
            "  • بنود حُدِّثت: %(c_items_updated)d\n"
            "  • بنود تخطّيتها (موجودة): %(c_items_skipped)d\n"
            "  • مسارات أودو مُحدَّثة: %(c_odoo_mapping_updated)d\n"
            "  • صياغات تدريبية أُنشئت: %(c_variants_created)d\n"
            "  • مواصفات دقيقة أُنشئت: %(c_specs_created)d\n\n"
            "── ملف B ──\n"
            "  • بنود تطابقت مع C وحُدِّثت صياغتها: %(b_items_matched_to_c)d\n"
            "  • صياغات «توريد وتركيب» جديدة على بنود قائمة: %(b_quotation_updated)d\n"
            "  • بنود جديدة من B (متخصّصة): %(b_items_created)d\n\n"
            "إجمالي البنود الفاعلة الآن: ≈ %(total_created)d\n\n"
            "%(errors_section)s"
        ) % {
            **stats,
            "total_created": total_created,
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
            "name": _("سجل البنود المرجعي"),
            "res_model": "rawasi.reference.item",
            "view_mode": "list,form",
            "context": {"import_summary_message": msg},
            "help": "<pre>" + msg + "</pre>",
        }
