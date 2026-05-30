# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, _, fields, models
from odoo.exceptions import UserError


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

    # ── المخزون: مواقع هرمية للعهدة ───────────────────────────────
    rawasi_project_location_id = fields.Many2one(
        "stock.location",
        string="مخزن المشروع",
        copy=False,
        help="موقع جذر يحتوي مواد المشروع. يُنشأ تلقائياً عند تفعيل «مشروع مقاولات».",
    )
    rawasi_main_stock_location_id = fields.Many2one(
        "stock.location",
        string="المخزن الرئيسي للمشروع",
        copy=False,
        help="موقع تخزين المواد المستلمة قبل صرفها لعهد المهندسين.",
    )
    rawasi_wip_location_id = fields.Many2one(
        "stock.location",
        string="موقع التنفيذ (WIP)",
        copy=False,
        help="موقع إنتاج (production) تُستهلك إليه المواد عند تأكيد DSR.",
    )
    rawasi_custody_root_location_id = fields.Many2one(
        "stock.location",
        string="جذر عُهد المهندسين",
        copy=False,
        help="الموقع الأبوي لكل عُهد المهندسين في هذا المشروع.",
    )
    rawasi_custody_ids = fields.One2many(
        "rawasi.engineer.custody", "project_id", string="عُهد المهندسين"
    )
    rawasi_custody_count = fields.Integer(
        compute="_compute_rawasi_custody_count", string="عدد العُهد",
    )

    @api.depends("rawasi_custody_ids")
    def _compute_rawasi_custody_count(self):
        for project in self:
            project.rawasi_custody_count = len(project.rawasi_custody_ids)

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("rawasi_is_construction") and not vals.get("rawasi_serial"):
                vals["rawasi_serial"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.project.serial"
                ) or False
        projects = super().create(vals_list)
        for project in projects.filtered("rawasi_is_construction"):
            project._ensure_rawasi_project_location()
            project._sync_engineer_custodies()
        return projects

    def write(self, vals):
        res = super().write(vals)
        if vals.get("rawasi_is_construction"):
            for project in self.filtered("rawasi_is_construction"):
                project._ensure_rawasi_project_location()
        if "site_engineer_ids" in vals or "rawasi_is_construction" in vals:
            for project in self.filtered("rawasi_is_construction"):
                project._sync_engineer_custodies()
        return res

    # ── إنشاء/مزامنة مواقع المخزون ─────────────────────────────────
    def _get_root_construction_location(self):
        """يعيد جذر «مشاريع المقاولات» داخل المخزن الافتراضي، ينشئه عند اللزوم."""
        self.ensure_one()
        Location = self.env["stock.location"]
        company = self.company_id or self.env.company
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1,
        )
        if not warehouse:
            raise UserError(_(
                "لا يوجد مخزن (Warehouse) مهيأ لشركة %s. أنشئ مخزناً من Inventory أولاً."
            ) % (company.name,))
        stock_loc = warehouse.lot_stock_id
        root = Location.search([
            ("name", "=", "مشاريع المقاولات"),
            ("location_id", "=", stock_loc.id),
            ("company_id", "=", company.id),
        ], limit=1)
        if not root:
            root = Location.create({
                "name": "مشاريع المقاولات",
                "usage": "internal",
                "location_id": stock_loc.id,
                "company_id": company.id,
            })
        return root

    def _ensure_rawasi_project_location(self):
        """يضمن إنشاء البنية الهرمية: مشروع → مخزن رئيسي + جذر العُهد."""
        Location = self.env["stock.location"]
        for project in self:
            if not project.rawasi_is_construction:
                continue
            if project.rawasi_project_location_id and \
               project.rawasi_main_stock_location_id and \
               project.rawasi_custody_root_location_id and \
               project.rawasi_wip_location_id:
                continue
            company_id = (project.company_id or self.env.company).id
            root = project._get_root_construction_location()
            if not project.rawasi_project_location_id:
                project.rawasi_project_location_id = Location.create({
                    "name": project.name or "Project %d" % project.id,
                    "usage": "internal",
                    "location_id": root.id,
                    "company_id": company_id,
                    "is_rawasi_project": True,
                    "rawasi_project_id": project.id,
                }).id
            project_loc = project.rawasi_project_location_id
            if not project.rawasi_main_stock_location_id:
                project.rawasi_main_stock_location_id = Location.create({
                    "name": "المخزن الرئيسي",
                    "usage": "internal",
                    "location_id": project_loc.id,
                    "company_id": company_id,
                    "rawasi_project_id": project.id,
                }).id
            if not project.rawasi_custody_root_location_id:
                project.rawasi_custody_root_location_id = Location.create({
                    "name": "عُهد المهندسين",
                    "usage": "view",
                    "location_id": project_loc.id,
                    "company_id": company_id,
                    "rawasi_project_id": project.id,
                }).id
            if not project.rawasi_wip_location_id:
                project.rawasi_wip_location_id = Location.create({
                    "name": "تنفيذ الموقع (WIP)",
                    "usage": "production",
                    "location_id": project_loc.id,
                    "company_id": company_id,
                    "rawasi_project_id": project.id,
                }).id

    def _sync_engineer_custodies(self):
        """يُنشئ عهدة لكل مهندس موقع غير ممثَّل بعد."""
        Custody = self.env["rawasi.engineer.custody"]
        for project in self:
            if not project.rawasi_is_construction:
                continue
            for user in project.site_engineer_ids:
                Custody._ensure_for(project, user)

    def action_open_custodies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("عُهد المهندسين"),
            "res_model": "rawasi.engineer.custody",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_project_inventory(self):
        self.ensure_one()
        if not self.rawasi_project_location_id:
            self._ensure_rawasi_project_location()
        return {
            "type": "ir.actions.act_window",
            "name": _("جرد المشروع"),
            "res_model": "stock.quant",
            "view_mode": "list",
            "domain": [("location_id", "child_of", self.rawasi_project_location_id.id)],
        }

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
