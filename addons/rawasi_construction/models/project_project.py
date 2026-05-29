# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, _, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"
    _rec_names_search = ["name", "rawasi_serial"]

    # مشروع إنشائي تابع لنظام رواسي سما (لتمييزه عن مشاريع أودو/الورشة العامة)
    rawasi_is_construction = fields.Boolean(string="مشروع مقاولات", default=False)
    rawasi_serial = fields.Char(
        string="الرقم التسلسلي", readonly=True, copy=False, index=True,
        help="رقم تسلسلي تلقائي بصيغة RS-PRJ-YYYY##### يربط المشروع بكل تفاصيله.",
    )
    site_engineer_ids = fields.Many2many(
        "res.users",
        "rawasi_project_site_engineer_rel",
        "project_id", "user_id",
        string="مهندسو الموقع",
        help="مهندسو الموقع المسؤولون عن هذا المشروع — مفتاح عزل مقاولي الباطن ومستخلصاتهم.",
    )
    rawasi_competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المصدر", readonly=True
    )
    rawasi_boq_item_ids = fields.Many2many(
        "rawasi.boq.item",
        string="بنود جدول الكميات",
        compute="_compute_rawasi_boq_item_ids",
    )
    rawasi_boq_item_count = fields.Integer(
        string="عدد البنود", compute="_compute_rawasi_boq_item_ids",
    )
    rawasi_currency_id = fields.Many2one(
        related="company_id.currency_id", string="عملة المقاولات",
    )
    rawasi_budget_total = fields.Monetary(
        string="الميزانية التعاقدية", compute="_compute_rawasi_budget",
        currency_field="rawasi_currency_id",
    )
    rawasi_budget_consumed = fields.Monetary(
        string="المستهلك", compute="_compute_rawasi_budget",
        currency_field="rawasi_currency_id",
    )
    rawasi_budget_remaining = fields.Monetary(
        string="المتبقي", compute="_compute_rawasi_budget",
        currency_field="rawasi_currency_id",
    )

    wbs_activity_ids = fields.One2many(
        "rawasi.wbs.activity", "project_id", string="أنشطة WBS"
    )
    wbs_count = fields.Integer(string="عدد الأنشطة", compute="_compute_wbs_count")

    @api.depends(
        "rawasi_competition_id.boq_item_ids.total_cost",
        "rawasi_competition_id.boq_item_ids.amount_consumed",
    )
    def _compute_rawasi_budget(self):
        for project in self:
            items = project.rawasi_competition_id.boq_item_ids
            total = sum(items.mapped("total_cost"))
            consumed = sum(items.mapped("amount_consumed"))
            project.rawasi_budget_total = total
            project.rawasi_budget_consumed = consumed
            project.rawasi_budget_remaining = total - consumed

    # ملاحظة: نستخدم بادئة rawasi_ لتفادي التعارض مع حقول موديولات أخرى
    # (مثل documents_project الذي يعرّف document_ids/document_count على المشروع).
    rawasi_document_ids = fields.One2many("rawasi.document", "project_id", string="المستندات")
    rawasi_mas_ids = fields.One2many("rawasi.material.approval", "project_id", string="اعتمادات المواد")
    rawasi_dsr_ids = fields.One2many("rawasi.daily.report", "project_id", string="التقارير اليومية")
    rawasi_ncr_ids = fields.One2many("rawasi.ncr", "project_id", string="تقارير عدم المطابقة")
    rawasi_rfi_ids = fields.One2many("rawasi.rfi", "project_id", string="طلبات المعلومات")

    rawasi_document_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_mas_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_dsr_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_ncr_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_rfi_count = fields.Integer(compute="_compute_rawasi_phase4_counts")

    # ═══ Smart Button counters للمشتريات والعقود ═══
    rawasi_mr_count = fields.Integer(compute="_compute_rawasi_procurement_counts")
    rawasi_po_count = fields.Integer(compute="_compute_rawasi_procurement_counts")
    rawasi_grn_count = fields.Integer(compute="_compute_rawasi_procurement_counts")
    rawasi_vo_count = fields.Integer(compute="_compute_rawasi_contract_counts")
    rawasi_ipc_count = fields.Integer(compute="_compute_rawasi_contract_counts")
    rawasi_bg_count = fields.Integer(compute="_compute_rawasi_contract_counts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("rawasi_is_construction") and not vals.get("rawasi_serial"):
                vals["rawasi_serial"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.project.serial"
                ) or False
        return super().create(vals_list)

    def _compute_wbs_count(self):
        for project in self:
            project.wbs_count = len(project.wbs_activity_ids)

    @api.depends("rawasi_competition_id.boq_item_ids")
    def _compute_rawasi_boq_item_ids(self):
        for project in self:
            items = project.rawasi_competition_id.boq_item_ids
            project.rawasi_boq_item_ids = items
            project.rawasi_boq_item_count = len(items)

    def action_open_boq_items(self):
        self.ensure_one()
        if not self.rawasi_competition_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("جدول الكميات"),
            "res_model": "rawasi.boq.item",
            "view_mode": "list,form",
            "domain": [("competition_id", "=", self.rawasi_competition_id.id)],
            "context": {"default_competition_id": self.rawasi_competition_id.id},
        }

    def _compute_rawasi_phase4_counts(self):
        for project in self:
            project.rawasi_document_count = len(project.rawasi_document_ids)
            project.rawasi_mas_count = len(project.rawasi_mas_ids)
            project.rawasi_dsr_count = len(project.rawasi_dsr_ids)
            project.rawasi_ncr_count = len(project.rawasi_ncr_ids)
            project.rawasi_rfi_count = len(project.rawasi_rfi_ids)

    def _rawasi_open_related(self, name, model):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_documents(self):
        return self._rawasi_open_related(_("المستندات"), "rawasi.document")

    def action_open_mas(self):
        return self._rawasi_open_related(_("اعتمادات المواد"), "rawasi.material.approval")

    def action_open_dsr(self):
        return self._rawasi_open_related(_("التقارير اليومية"), "rawasi.daily.report")

    def action_open_ncr(self):
        return self._rawasi_open_related(_("تقارير عدم المطابقة"), "rawasi.ncr")

    def action_open_rfi(self):
        return self._rawasi_open_related(_("طلبات المعلومات"), "rawasi.rfi")

    # ═══ counters/actions للمشتريات والعقود ═══
    def _compute_rawasi_procurement_counts(self):
        MR = self.env["rawasi.material.request"]
        PO = self.env["rawasi.purchase.order"]
        GR = self.env["rawasi.goods.receipt"]
        for project in self:
            domain = [("project_id", "=", project.id)]
            project.rawasi_mr_count = MR.search_count(domain)
            project.rawasi_po_count = PO.search_count(domain)
            project.rawasi_grn_count = GR.search_count(domain)

    def _compute_rawasi_contract_counts(self):
        VO = self.env["rawasi.variation.order"]
        IPC = self.env["rawasi.payment.certificate"]
        BG = self.env["rawasi.bank.guarantee"]
        for project in self:
            domain = [("project_id", "=", project.id)]
            project.rawasi_vo_count = VO.search_count(domain)
            project.rawasi_ipc_count = IPC.search_count(domain)
            project.rawasi_bg_count = BG.search_count(domain)

    def action_open_mr(self):
        return self._rawasi_open_related(_("طلبات المواد"), "rawasi.material.request")

    def action_open_po(self):
        return self._rawasi_open_related(_("أوامر الشراء"), "rawasi.purchase.order")

    def action_open_grn(self):
        return self._rawasi_open_related(_("سندات الاستلام"), "rawasi.goods.receipt")

    def action_open_vo(self):
        return self._rawasi_open_related(_("أوامر التغيير"), "rawasi.variation.order")

    def action_open_ipc(self):
        return self._rawasi_open_related(_("المستخلصات"), "rawasi.payment.certificate")

    def action_open_bg(self):
        return self._rawasi_open_related(_("الضمانات البنكية"), "rawasi.bank.guarantee")

    def action_generate_wbs_phases(self):
        """يولّد المراحل الرئيسية الست (من القوالب) كأنشطة عليا مع مهامها الفرعية،
        ويُسند تواريخ افتراضية متسلسلة لتظهر مباشرةً على الجدول الزمني (Gantt)."""
        Activity = self.env["rawasi.wbs.activity"]
        phases = self.env["rawasi.wbs.phase"].search([], order="sequence")
        today = fields.Date.context_today(self)
        phase_days = 30
        for project in self:
            existing = project.wbs_activity_ids.filtered(
                lambda a: a.phase_id and not a.parent_id
            )
            existing_phase_ids = existing.mapped("phase_id")
            start = project.date_start or today
            if hasattr(start, "date"):  # في حال كان Datetime
                start = start.date()
            cursor = start
            seq = 10
            for phase in phases:
                if phase in existing_phase_ids:
                    continue
                p_start = cursor
                p_end = cursor + timedelta(days=phase_days - 1)
                parent = Activity.create({
                    "project_id": project.id,
                    "phase_id": phase.id,
                    "name": ("%s %s" % (phase.code, phase.name)) if phase.code else phase.name,
                    "sequence": seq,
                    "date_start": p_start,
                    "date_end": p_end,
                })
                tasks = phase.task_ids
                n = len(tasks)
                span = max(1, phase_days // n) if n else phase_days
                tcursor = p_start
                tseq = 10
                for i, task in enumerate(tasks):
                    t_start = tcursor
                    t_end = p_end if i == n - 1 else min(
                        p_end, tcursor + timedelta(days=span - 1)
                    )
                    Activity.create({
                        "project_id": project.id,
                        "phase_id": phase.id,
                        "parent_id": parent.id,
                        "name": task.name,
                        "sequence": tseq,
                        "date_start": t_start,
                        "date_end": t_end,
                    })
                    tcursor = t_end + timedelta(days=1)
                    tseq += 10
                cursor = p_end + timedelta(days=1)
                seq += 10
        return self.action_open_wbs()

    # ── المسار الحرج (CPM) وطباعة الجدول الزمني ──────────────────
    def _compute_wbs_critical_path(self):
        """يحسب المسار الحرج (CPM) على الأنشطة الورقية عبر علاقات الأسبقية والمدد،
        ويعيّن is_critical/total_float. الأنشطة الأب حرجة إن كان أحد أبنائها حرجاً."""
        for project in self:
            acts = project.wbs_activity_ids
            leaves = acts.filtered(lambda a: not a.child_ids and a.date_start and a.date_end)
            leaf_ids = set(leaves.ids)

            def _dur(a):
                return max((a.date_end - a.date_start).days + 1, 1)

            dur = {a.id: _dur(a) for a in leaves}
            preds = {
                a.id: [p.id for p in a.predecessor_ids if p.id in leaf_ids]
                for a in leaves
            }
            succ = {aid: [] for aid in leaf_ids}
            for aid, plist in preds.items():
                for p in plist:
                    succ[p].append(aid)

            ef = {}

            def calc_ef(aid, stack):
                if aid in ef:
                    return ef[aid]
                if aid in stack:
                    return dur[aid]
                base = max([calc_ef(p, stack | {aid}) for p in preds[aid]], default=0)
                ef[aid] = base + dur[aid]
                return ef[aid]

            for aid in leaf_ids:
                calc_ef(aid, set())
            project_end = max(ef.values(), default=0)
            es = {aid: ef[aid] - dur[aid] for aid in leaf_ids}

            lf = {}

            def calc_lf(aid, stack):
                if aid in lf:
                    return lf[aid]
                if aid in stack:
                    return project_end
                lf[aid] = min(
                    [calc_lf(s, stack | {aid}) - dur[s] for s in succ[aid]],
                    default=project_end,
                )
                return lf[aid]

            for aid in leaf_ids:
                calc_lf(aid, set())

            for a in leaves:
                tf = (lf[a.id] - dur[a.id]) - es[a.id]
                a.total_float = tf
                a.is_critical = tf <= 0
            for a in acts.filtered(lambda x: x.child_ids):
                crit = any(a.child_ids.mapped("is_critical"))
                a.is_critical = crit
                a.total_float = 0

    def _schedule_report_lines(self):
        """يبني بيانات مخطط الجدول الزمني (Gantt) للطباعة: نِسَب الإزاحة والعرض
        لكل نشاط على محور زمني، مع لون (حرج/معلَم/عادي) وأشهر المحور."""
        self.ensure_one()
        acts = self.wbs_activity_ids.filtered(
            lambda a: a.date_start and a.date_end
        ).sorted(key=lambda a: (a.sequence, a.date_start, a.id))
        if not acts:
            return {"lines": [], "periods": [], "total": 0}
        pmin = min(acts.mapped("date_start"))
        pmax = max(acts.mapped("date_end"))
        total = max((pmax - pmin).days + 1, 1)
        lines = []
        for a in acts:
            offset = (a.date_start - pmin).days
            width = (a.date_end - a.date_start).days + 1
            if a.is_critical:
                color = "#d9534f"
            elif a.is_milestone:
                color = "#6f42c1"
            else:
                color = "#4a90d2"
            offset_pct = round(offset * 100.0 / total, 2)
            width_pct = round(max(width, 1) * 100.0 / total, 2)
            bar_style = (
                f"position:absolute;left:{offset_pct}%;width:{width_pct}%;"
                f"background:{color};height:11px;border-radius:2px;"
            )
            lines.append({
                "name": a.name,
                "level": 1 if a.parent_id else 0,
                "date_start": a.date_start,
                "date_end": a.date_end,
                "duration": a.duration,
                "total_float": a.total_float,
                "is_critical": a.is_critical,
                "bar_style": bar_style,
            })
        # أعمدة الأشهر للمحور الزمني
        periods = []
        y, m = pmin.year, pmin.month
        from datetime import date as _date
        cur = _date(y, m, 1)
        while cur <= pmax:
            nm_y, nm_m = (y + 1, 1) if m == 12 else (y, m + 1)
            nxt = _date(nm_y, nm_m, 1)
            seg_start = max(cur, pmin)
            offset = (seg_start - pmin).days
            offset_pct = round(offset * 100.0 / total, 2)
            periods.append({
                "label": "%02d/%04d" % (m, y),
                "style": (
                    f"position:absolute;left:{offset_pct}%;font-size:7px;"
                    f"border-left:1px solid #ccc;padding-left:1px;"
                ),
            })
            y, m, cur = nm_y, nm_m, nxt
        return {"lines": lines, "periods": periods, "total": total}

    def action_print_schedule(self):
        self.ensure_one()
        self._compute_wbs_critical_path()
        return self.env.ref(
            "rawasi_construction.action_report_schedule"
        ).report_action(self)

    def action_open_wbs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("هيكل تجزئة العمل (WBS)"),
            "res_model": "rawasi.wbs.activity",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_schedule_import(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("استيراد الجدول الزمني"),
            "res_model": "rawasi.schedule.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_download_schedule_template(self):
        """تنزيل قالب Excel للجدول الزمني (بكل الحقول) مباشرةً من المشروع."""
        return self.env["rawasi.schedule.import.wizard"].action_download_template()
