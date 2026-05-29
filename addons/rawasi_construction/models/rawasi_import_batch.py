# -*- coding: utf-8 -*-
"""دفعة استيراد جدول كميات.

يجب ربطها بمنافسة (linked_tender) بشكل إلزامي. تخزّن ملف Excel الأصلي
+ سطوره الخام + نتائج المطابقة + قرارات المراجعة.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ImportBatch(models.Model):
    _name = "rawasi.import.batch"
    _description = "دفعة استيراد جدول كميات — Import Batch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "upload_date desc"
    _rec_name = "filename"

    filename = fields.Char(string="اسم الملف", required=True, tracking=True)
    file_data = fields.Binary(
        string="ملف Excel", attachment=True, required=True,
    )
    upload_date = fields.Datetime(
        string="تاريخ الرفع", default=fields.Datetime.now,
        readonly=True, index=True,
    )
    uploaded_by_user_id = fields.Many2one(
        "res.users", string="رفعه",
        default=lambda self: self.env.user, readonly=True,
    )
    # ── الربط الإلزامي بالمنافسة ─────────────────────────────────
    linked_tender_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المرتبطة",
        required=True, ondelete="restrict", index=True, tracking=True,
        help="المنافسة التي ستنتقل لها بنود جدول الكميات بعد الاعتماد. "
             "إلزامية في كل استيراد.",
    )
    source_entity_id = fields.Many2one(
        "res.partner", string="الجهة المصدر",
    )
    notes = fields.Text(string="ملاحظات")

    state = fields.Selection(
        [
            ("draft",     "مسودة"),
            ("analyzing", "قيد التحليل"),
            ("reviewing", "قيد المراجعة"),
            ("approved",  "معتمَدة"),
            ("cancelled", "ملغاة"),
        ],
        string="الحالة", default="draft", required=True,
        tracking=True, index=True,
    )

    import_batch_line_ids = fields.One2many(
        "rawasi.import.batch.line", "import_batch_id",
        string="سطور الجدول المُستلَمة",
    )

    # ── عدادات المراجعة ──────────────────────────────────────────
    total_lines    = fields.Integer(compute="_compute_counts", store=True)
    matched_lines  = fields.Integer(compute="_compute_counts", store=True,
                                    string="السطور المطابَقة")
    pending_lines  = fields.Integer(compute="_compute_counts", store=True,
                                    string="بانتظار المراجعة")
    accepted_lines = fields.Integer(compute="_compute_counts", store=True,
                                    string="السطور المقبولة")
    saved_lines    = fields.Integer(compute="_compute_counts", store=True,
                                    string="السطور المحفوظة")
    rejected_lines = fields.Integer(compute="_compute_counts", store=True,
                                    string="السطور المرفوضة")

    @api.depends("import_batch_line_ids", "import_batch_line_ids.review_status",
                 "import_batch_line_ids.suggested_match_id")
    def _compute_counts(self):
        for batch in self:
            lines = batch.import_batch_line_ids
            batch.total_lines = len(lines)
            batch.matched_lines = len(lines.filtered(lambda l: l.suggested_match_id))
            batch.pending_lines = len(lines.filtered(lambda l: l.review_status == "pending"))
            batch.accepted_lines = len(lines.filtered(
                lambda l: l.review_status in ("accepted", "modified", "created_new")
            ))
            batch.saved_lines = len(lines.filtered(lambda l: l.review_status == "saved"))
            batch.rejected_lines = len(lines.filtered(lambda l: l.review_status == "rejected"))

    # ── أزرار سير الحالات ────────────────────────────────────────
    def action_open_review(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("مراجعة دفعة: %s") % self.filename,
            "res_model": "rawasi.import.batch.line",
            "view_mode": "list,form",
            "domain": [("import_batch_id", "=", self.id)],
            "context": {
                "default_import_batch_id": self.id,
                "search_default_pending": 1,
            },
        }

    def action_cancel(self):
        for batch in self:
            batch.state = "cancelled"

    def action_reject_all_pending(self):
        for batch in self:
            pending = batch.import_batch_line_ids.filtered(
                lambda l: l.review_status == "pending"
            )
            if pending:
                pending.write({"review_status": "rejected", "final_match_id": False})

    def action_accept_all_high_confidence(self):
        for batch in self:
            candidates = batch.import_batch_line_ids.filtered(
                lambda l: (l.review_status == "pending"
                          and l.suggested_match_id
                          and l.suggestion_confidence >= 85.0)
            )
            for line in candidates:
                line.write({
                    "review_status": "accepted",
                    "final_match_id": line.suggested_match_id.id,
                })

    def action_import_approval(self):
        """اعتماد الاستيراد — يُرحّل البنود المعتمدة لـ rawasi.boq.item على
        المنافسة المرتبطة، يحدّث الصياغات البديلة، يسجّل التتبع."""
        self.ensure_one()
        if self.state in ("approved", "cancelled"):
            raise UserError(_("الدفعة في حالة «%s» — لا يمكن اعتمادها.") % self.state)
        if not self.linked_tender_id:
            raise UserError(_("الدفعة بلا منافسة مرتبطة. لا يمكن الاعتماد."))

        # السطور المعلَّقة تأخذ قراراً تلقائياً
        auto_accepted = 0
        auto_saved = 0
        for line in self.import_batch_line_ids.filtered(
            lambda l: l.review_status == "pending"
        ):
            if line.suggested_match_id:
                line.write({
                    "review_status": "accepted",
                    "final_match_id": line.suggested_match_id.id,
                })
                auto_accepted += 1
            else:
                line.write({"review_status": "saved", "final_match_id": False})
                auto_saved += 1

        Variant = self.env["rawasi.item.variant"]
        Audit = self.env["rawasi.audit.trail"]
        BoqItem = self.env["rawasi.boq.item"]
        from odoo.addons.rawasi_construction.models.rawasi_item_variant import (
            normalize_for_matching,
        )

        created_boq = 0
        for line in self.import_batch_line_ids:
            # سطر محفوظ بلا ترشيح: لا variant، نسجّل في audit، ننشئ BOQ بدون ربط
            if line.review_status == "saved":
                Audit.create({
                    "original_text": line.original_text,
                    "reference_item_id": False,
                    "match_source": line.suggestion_source or "none",
                    "confidence_score": line.suggestion_confidence,
                    "user_action": "saved_no_match",
                    "import_batch_id": self.id,
                    "linked_tender_id": self.linked_tender_id.id,
                })
                BoqItem.create(line._build_boq_values(self.linked_tender_id))
                created_boq += 1
                continue

            # سطر مرفوض: لا variant، لا BOQ، صف في audit فقط
            if line.review_status == "rejected":
                Audit.create({
                    "original_text": line.original_text,
                    "reference_item_id": False,
                    "match_source": line.suggestion_source or "none",
                    "confidence_score": line.suggestion_confidence,
                    "user_action": "rejected",
                    "import_batch_id": self.id,
                    "linked_tender_id": self.linked_tender_id.id,
                })
                continue

            ref = line.final_match_id or line.suggested_match_id
            if not ref:
                continue

            # نضمن وجود الصياغة البديلة لهذا البند المرجعي
            normalized = normalize_for_matching(line.original_text or "")
            existing = Variant.search([
                ("reference_item_id", "=", ref.id),
                ("normalized_text", "=", normalized),
            ], limit=1)
            if existing:
                existing.write({
                    "frequency": existing.frequency + 1,
                    "last_seen_date": fields.Date.context_today(self),
                })
            else:
                Variant.create({
                    "reference_item_id": ref.id,
                    "original_text": line.original_text,
                    "source_entity_id": self.source_entity_id.id or False,
                    "frequency": 1,
                })

            # تعبئة الوصف الكامل من الجهة (مرة واحدة — أول مطابقة فقط)
            # لو الحقل فارغ ولدينا نص كامل من Excel، نحفظه كمرجع رسمي للبند.
            if not ref.government_text and line.original_text:
                ref.government_text = line.original_text

            # سجل تتبع
            Audit.create({
                "original_text": line.original_text,
                "reference_item_id": ref.id,
                "match_source": line.suggestion_source or "manual",
                "confidence_score": line.suggestion_confidence,
                "user_action": line.review_status,
                "original_suggestion_id": (
                    line.suggested_match_id.id if line.suggested_match_id
                    and line.suggested_match_id != ref else False
                ),
                "import_batch_id": self.id,
                "linked_tender_id": self.linked_tender_id.id,
            })

            # ننشئ بند BOQ على المنافسة + نربطه بالبند المرجعي
            vals = line._build_boq_values(self.linked_tender_id)
            vals["reference_item_id"] = ref.id
            BoqItem.create(vals)
            created_boq += 1

        self.state = "approved"
        self.message_post(body=_(
            "تم اعتماد الاستيراد — أُضيف %d بند(اً) للمنافسة «%s»."
        ) % (created_boq, self.linked_tender_id.name))

        return {
            "type": "ir.actions.act_window",
            "name": _("المنافسة"),
            "res_model": "rawasi.competition",
            "res_id": self.linked_tender_id.id,
            "view_mode": "form",
            "target": "current",
        }
