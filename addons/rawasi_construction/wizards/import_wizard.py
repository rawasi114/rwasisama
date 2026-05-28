# -*- coding: utf-8 -*-
"""معالج استيراد جدول كميات من اعتماد (Etimad).

يستقبل ملف Excel، يقرأ سطوره، ينظّفها، يطبّق محرك المطابقة الذكية،
ويُنشئ دفعة استيراد + سطور خام جاهزة للمراجعة.
"""
import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.rawasi_construction.services import matching_engine
from odoo.addons.rawasi_construction.services import unit_normalizer
from odoo.addons.rawasi_construction.services import spec_extractor

_logger = logging.getLogger(__name__)


# ── Mapping أعمدة اعتماد القياسية ────────────────────────────────
_COL_ALIASES = {
    "serial":    ("الرقم التسلسلي", "الرقم", "م", "Serial"),
    "category":  ("الفئة", "Category"),
    "group":     ("البند", "Item"),
    "unit":      ("وحدة القياس", "الوحدة", "Unit"),
    "quantity":  ("الكمية", "Quantity", "Qty"),
    "desc":      ("وصف البند", "الوصف", "Description"),
    "specs":     ("المواصفات", "Specifications", "Specs"),
    "lcgpa":     ("الرمز الإنشائي", "LCGPA", "LCGPA Code", "كود LCGPA"),
    "mandatory": ("منتج من القائمة الإلزامية", "إلزامي محلي", "Mandatory"),
}


def _detect_columns(header_row):
    """يرجع dict: field_key → column_index في الـ Excel."""
    mapping = {}
    for col_idx, cell in enumerate(header_row):
        if not cell:
            continue
        cell_clean = str(cell).strip()
        for key, aliases in _COL_ALIASES.items():
            if cell_clean in aliases:
                mapping[key] = col_idx
                break
    return mapping


class ImportWizard(models.TransientModel):
    _name = "rawasi.import.wizard"
    _description = "معالج استيراد جدول كميات (Etimad Import Wizard)"

    file_data = fields.Binary(string="ملف Excel", required=True)
    filename = fields.Char(string="اسم الملف", required=True)
    source_entity_id = fields.Many2one(
        "res.partner", string="الجهة المصدر",
        help="الجهة الحكومية التي صدر منها الملف (اختياري).",
    )
    competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المرتبطة",
    )

    def action_analyze(self):
        """يقرأ ملف Excel، ينشئ دفعة + سطور، يشغّل محرك المطابقة، ثم
        يفتح شاشة المراجعة على الدفعة الجديدة."""
        self.ensure_one()
        try:
            import openpyxl
        except ImportError:
            raise UserError(_(
                "مكتبة openpyxl غير متوفّرة. ثبّتها على الخادم."
            ))
        try:
            wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(self.file_data)),
                                         data_only=True)
        except Exception as e:
            raise UserError(_("تعذّر فتح الملف: %s") % e)

        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise UserError(_("الملف فارغ."))

        # Detect header row
        header_idx = None
        for i, r in enumerate(rows):
            if r and any(c == "وصف البند" for c in r if c):
                header_idx = i
                break
        if header_idx is None:
            raise UserError(_("لم أتمكّن من تحديد صف العناوين — يجب أن يحوي «وصف البند»."))
        col_map = _detect_columns(rows[header_idx])
        if "desc" not in col_map:
            raise UserError(_("عمود «وصف البند» غير موجود في الملف."))

        # Create batch
        batch = self.env["rawasi.import.batch"].create({
            "filename": self.filename,
            "file_data": self.file_data,
            "source_entity_id": self.source_entity_id.id or False,
            "competition_id": self.competition_id.id or False,
            "state": "analyzing",
        })

        last_category = None
        last_group = None
        line_num = 0
        for r in rows[header_idx + 1:]:
            if not r or not any(r):
                continue

            def get(key):
                idx = col_map.get(key)
                if idx is None or idx >= len(r) or r[idx] is None:
                    return None
                v = str(r[idx]).strip()
                return v if v else None

            desc = get("desc")
            if not desc:
                continue
            line_num += 1

            cat = get("category")
            grp = get("group")
            if cat: last_category = cat
            if grp: last_group = grp

            unit_raw = get("unit") or ""
            lcgpa_raw = get("lcgpa") or ""
            uom = unit_normalizer.get_uom_record(self.env, unit_raw)
            specs = spec_extractor.extract_all(desc)

            # Run matching engine
            ref, conf, source = matching_engine.find_match(
                self.env, desc, lcgpa_raw=lcgpa_raw, extracted_specs=specs,
            )

            # Detect LCGPA code record
            detected_lcgpa = False
            if lcgpa_raw and lcgpa_raw.strip() and lcgpa_raw.lower() not in ("غير محدد", "لا يوجد"):
                lc = self.env["rawasi.lcgpa.code"].search(
                    [("code", "=", lcgpa_raw.strip())], limit=1,
                )
                if lc:
                    detected_lcgpa = lc.id

            self.env["rawasi.import.raw.line"].create({
                "batch_id": batch.id,
                "line_number": line_num,
                "original_text": desc,
                "original_unit": unit_raw or False,
                "original_quantity": get("quantity") or False,
                "original_category": cat or (last_category if cat else False),
                "original_item_group": grp or (last_group if grp else False),
                "original_specs": get("specs") or False,
                "original_lcgpa_raw": lcgpa_raw or False,
                "original_mandatory_local": get("mandatory") or False,
                "normalized_unit_id": uom.id if uom else False,
                "detected_lcgpa_id": detected_lcgpa,
                "suggested_match_id": ref.id if ref else False,
                "suggestion_confidence": conf,
                "suggestion_source": source,
                "extracted_dimensions": specs.get("dimensions") or False,
                "extracted_thickness": specs.get("thickness") or False,
                "extracted_diameter": specs.get("diameter") or False,
                "extracted_strength": specs.get("strength") or False,
            })

        batch.state = "reviewing"
        batch.message_post(body=_(
            "تم تحليل %d سطر — افتح شاشة المراجعة لاتخاذ القرارات."
        ) % line_num)

        return {
            "type": "ir.actions.act_window",
            "name": _("مراجعة الاستيراد"),
            "res_model": "rawasi.import.batch",
            "res_id": batch.id,
            "view_mode": "form",
            "target": "current",
        }
