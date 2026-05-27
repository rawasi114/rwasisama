"""Wizard for uploading and confirming BoQ files.

This wizard talks to the FastAPI backend to do the actual parsing,
normalization, and persistence — the Odoo layer is just UI.
"""

from __future__ import annotations

import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


BOQ_TYPE_SELECTION = [
    ("original_tender", "جدول الكميات الأصلي للجهة"),
    ("rawasi", "جدول كميات رواسي سما"),
    ("competitor", "جدول كميات منافس"),
]

SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv", ".pdf")


class BoqImportWizard(models.TransientModel):
    _name = "rps.boq.import.wizard"
    _description = "Import BoQ from file"

    tender_id = fields.Many2one("rps.tender", string="المنافسة", required=True)
    boq_type = fields.Selection(
        BOQ_TYPE_SELECTION,
        string="نوع جدول الكميات",
        required=True,
        help="مهم جداً: نوع جدول الكميات يحدد كيف يعالجه المحرك التحليلي.",
    )

    @api.model
    def default_get(self, fields_list):
        """Auto-fill tender_id when the wizard is opened from a tender form/list.

        Safe both when there is no active record (menu entry) and when the
        wizard is launched via the Actions dropdown of a tender (binding).
        """
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        if active_model == "rps.tender" and active_id:
            res["tender_id"] = active_id
        return res
    source_competitor_id = fields.Many2one(
        "rps.competitor",
        string="المنافس صاحب الجدول",
        help="إلزامي عند اختيار 'جدول كميات منافس'.",
    )
    upload_file = fields.Binary(string="ملف جدول الكميات", required=True)
    upload_filename = fields.Char(string="اسم الملف")

    state = fields.Selection(
        [
            ("draft", "إعداد"),
            ("preview", "مراجعة البنود"),
            ("done", "تم الحفظ"),
        ],
        default="draft",
        readonly=True,
    )

    preview_json = fields.Text(string="بنود المراجعة (JSON)", readonly=True)
    source_file_id = fields.Char(string="معرّف الملف المخزّن", readonly=True)
    total_items = fields.Integer(string="إجمالي البنود", readonly=True)
    items_needing_review = fields.Integer(
        string="بنود تحتاج مراجعة بشرية", readonly=True
    )

    @api.constrains("boq_type", "source_competitor_id")
    def _check_competitor_required(self):
        for rec in self:
            if rec.boq_type == "competitor" and not rec.source_competitor_id:
                raise UserError(
                    _("اختر المنافس صاحب الجدول قبل المتابعة.")
                )
            if rec.boq_type != "competitor" and rec.source_competitor_id:
                raise UserError(
                    _("حقل المنافس يُستخدم فقط لنوع 'جدول كميات منافس'.")
                )

    @api.constrains("upload_filename")
    def _check_extension(self):
        for rec in self:
            if not rec.upload_filename:
                continue
            lower = rec.upload_filename.lower()
            if not any(lower.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                raise UserError(
                    _(
                        "صيغة الملف غير مدعومة. الصيغ المدعومة: %s"
                    )
                    % ", ".join(SUPPORTED_EXTENSIONS)
                )

    def action_upload(self):
        """Upload + parse + stage. Moves wizard to preview state."""
        self.ensure_one()
        if not self.upload_file:
            raise UserError(_("اختر ملف جدول الكميات أولاً."))

        client = self.env["rps.api.client"]
        file_bytes = base64.b64decode(self.upload_file)
        files = {
            "file": (self.upload_filename or "boq.xlsx", file_bytes),
        }
        data = {"boq_type": self.boq_type}
        if self.source_competitor_id and self.source_competitor_id.backend_id:
            data["source_competitor_id"] = self.source_competitor_id.backend_id

        try:
            response = client.request(
                "POST",
                f"/tenders/{self.tender_id.backend_id}/boq/upload",
                files=files,
                data=data,
            )
        except Exception as exc:
            raise UserError(
                _("فشل رفع الملف إلى الخادم: %s") % str(exc)
            ) from exc

        self.write(
            {
                "state": "preview",
                "preview_json": json.dumps(response, ensure_ascii=False),
                "source_file_id": response.get("source_file_id"),
                "total_items": response.get("total_items", 0),
                "items_needing_review": response.get("items_needing_review", 0),
            }
        )
        return self._reopen()

    def action_confirm(self):
        """Persist the staged items via the backend."""
        self.ensure_one()
        if self.state != "preview":
            raise UserError(_("لا توجد بنود للحفظ. ارفع الملف أولاً."))
        if not self.preview_json:
            raise UserError(_("بيانات المراجعة مفقودة."))

        preview = json.loads(self.preview_json)
        payload = {
            "boq_type": self.boq_type,
            "source_file_id": self.source_file_id,
            "source_competitor_id": (
                self.source_competitor_id.backend_id
                if self.source_competitor_id
                else None
            ),
            "items": preview.get("items", []),
        }
        client = self.env["rps.api.client"]
        try:
            result = client.request(
                "POST",
                f"/tenders/{self.tender_id.backend_id}/boq/confirm",
                json=payload,
            )
        except Exception as exc:
            raise UserError(
                _("فشل حفظ البنود: %s") % str(exc)
            ) from exc

        self.state = "done"
        message = _(
            "تم حفظ %d بند من جدول الكميات بنجاح."
        ) % result.get("items_committed", 0)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("نجاح"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_back_to_edit(self):
        self.state = "draft"
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
