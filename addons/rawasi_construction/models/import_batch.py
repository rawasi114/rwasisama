# -*- coding: utf-8 -*-
"""دفعة استيراد — كل ملف Excel من اعتماد يُحوَّل إلى دفعة واحدة تجمع كل
سطوره الخام مع نتائج المطابقة وقرارات المراجعة.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ImportBatch(models.Model):
    _name = "rawasi.import.batch"
    _description = "دفعة استيراد جدول كميات (Import Batch)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "upload_date desc"
    _rec_name = "filename"

    filename = fields.Char(string="اسم الملف", required=True, tracking=True)
    file_data = fields.Binary(string="ملف Excel", attachment=True)
    upload_date = fields.Datetime(
        string="تاريخ الرفع", default=fields.Datetime.now, readonly=True,
    )
    uploaded_by_user_id = fields.Many2one(
        "res.users", string="رفعه",
        default=lambda self: self.env.user, readonly=True,
    )
    source_entity_id = fields.Many2one(
        "res.partner", string="الجهة المصدر",
        help="الجهة الحكومية التي صدر منها هذا الملف.",
    )
    competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المرتبطة",
        help="اختياري — للربط مع منافسة معيَّنة.",
    )
    state = fields.Selection(
        [
            ("draft",     "مسودة"),
            ("analyzing", "قيد التحليل"),
            ("reviewing", "قيد المراجعة"),
            ("approved",  "معتمَدة"),
            ("cancelled", "ملغاة"),
        ],
        string="الحالة", default="draft", tracking=True, index=True,
    )

    raw_line_ids = fields.One2many(
        "rawasi.import.raw.line", "batch_id", string="السطور الخام",
    )

    # عدادات للمراجعة السريعة
    total_lines = fields.Integer(
        string="إجمالي السطور", compute="_compute_counts", store=True,
    )
    matched_lines = fields.Integer(
        string="السطور المطابَقة", compute="_compute_counts", store=True,
    )
    pending_lines = fields.Integer(
        string="بانتظار المراجعة", compute="_compute_counts", store=True,
    )
    accepted_lines = fields.Integer(
        string="السطور المقبولة", compute="_compute_counts", store=True,
    )
    rejected_lines = fields.Integer(
        string="السطور المرفوضة", compute="_compute_counts", store=True,
    )

    notes = fields.Text(string="ملاحظات")

    @api.depends("raw_line_ids.review_status")
    def _compute_counts(self):
        for batch in self:
            lines = batch.raw_line_ids
            batch.total_lines = len(lines)
            batch.matched_lines = len(lines.filtered(
                lambda l: l.suggested_match_id
            ))
            batch.pending_lines = len(lines.filtered(
                lambda l: l.review_status == "pending"
            ))
            batch.accepted_lines = len(lines.filtered(
                lambda l: l.review_status in ("accepted", "modified", "created_new")
            ))
            batch.rejected_lines = len(lines.filtered(
                lambda l: l.review_status == "rejected"
            ))

    # ── سير الحالات ─────────────────────────────────────────────
    def action_open_review(self):
        """يفتح شاشة المراجعة (List + Form للسطور) لهذه الدفعة."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("مراجعة دفعة: %s") % self.filename,
            "res_model": "rawasi.import.raw.line",
            "view_mode": "list,form",
            "domain": [("batch_id", "=", self.id)],
            "context": {
                "default_batch_id": self.id,
                "search_default_pending": 1,
            },
        }

    def action_approve_import(self):
        """اعتماد الاستيراد: يحفظ القرارات، يحدّث الصياغات البديلة،
        ويسجّل كل عملية في سجل التتبع. السطور المرفوضة تبقى مرفوضة."""
        self.ensure_one()
        if self.state not in ("reviewing", "draft", "analyzing"):
            raise UserError(_("الدفعة في حالة %s — لا يمكن اعتمادها.") % self.state)
        pending = self.raw_line_ids.filtered(lambda l: l.review_status == "pending")
        if pending:
            raise UserError(_(
                "%d سطر(اً) لا يزال بانتظار المراجعة. راجع كل السطور قبل الاعتماد."
            ) % len(pending))
        Audit = self.env["rawasi.audit.trail"]
        Variant = self.env["rawasi.item.variant"]
        for line in self.raw_line_ids:
            if line.review_status == "rejected":
                Audit.create({
                    "original_text": line.original_text,
                    "reference_item_id": False,
                    "match_source": line.suggestion_source or "manual",
                    "confidence_score": line.suggestion_confidence,
                    "user_action": "rejected",
                    "import_batch_id": self.id,
                })
                continue
            ref = line.final_match_id or line.suggested_match_id
            if not ref:
                continue
            # حدِّث / أنشئ الصياغة البديلة
            normalized = line._normalized_original()
            existing = Variant.search([
                ("reference_item_id", "=", ref.id),
                ("normalized_text", "=", normalized),
            ], limit=1)
            if existing:
                existing.frequency += 1
                existing.last_seen_date = fields.Date.context_today(self)
                if self.source_entity_id and not existing.source_entity_id:
                    existing.source_entity_id = self.source_entity_id
            else:
                Variant.create({
                    "reference_item_id": ref.id,
                    "original_text": line.original_text,
                    "source_entity_id": self.source_entity_id.id or False,
                    "frequency": 1,
                })
            # سجل قرار
            action = (
                "accepted" if line.review_status == "accepted"
                else "modified" if line.review_status == "modified"
                else "created_new" if line.review_status == "created_new"
                else "accepted"
            )
            Audit.create({
                "original_text": line.original_text,
                "reference_item_id": ref.id,
                "match_source": line.suggestion_source or "manual",
                "confidence_score": line.suggestion_confidence,
                "user_action": action,
                "original_suggestion_id":
                    line.suggested_match_id.id if line.suggested_match_id
                    and line.suggested_match_id != ref else False,
                "import_batch_id": self.id,
            })
        self.state = "approved"
        self.message_post(body=_("تم اعتماد الاستيراد — %d قرار سُجِّل في سجل التتبع.")
                          % len(self.raw_line_ids))
